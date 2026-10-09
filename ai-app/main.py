from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from search_qdrant import search_chunks, get_document_limits
from starlette.concurrency import run_in_threadpool
from qdrant_client.http.exceptions import ResponseHandlingException
from context_rules import evaluate_context
from typing import Literal

app = FastAPI()
MOCK_SERVICES_URL = os.getenv("MOCK_SERVICES_URL", "http://localhost:8001")

class Incident(BaseModel):
    incident_id: str
    application: str
    priority: str
    summary: str
    
class Monitoring(BaseModel):
    application: str
    status: str
    error_rate_percent: float
    latency_p95_ms: float

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

class ApplicationLogs(BaseModel):
    application: str
    entries: list[LogEntry]

class RunbookChunk(BaseModel):
    chunk_id: str
    document_id: str
    source: str
    section: str
    subsection: str | None = None
    content: str

class RetrievedDocument(BaseModel):
    score: float
    chunk: RunbookChunk

class InvestigationContext(BaseModel):
    incident: Incident
    monitoring: Monitoring
    logs: ApplicationLogs
    documentation: list[RetrievedDocument]
    document_limits: list[RunbookChunk]
    documentation_status: Literal["retrieved", "no_matches"]
    analysis_status: Literal["context_ready", "abstained"]
    analysis_reason: str
    analysis_code: Literal[
        "NO_DOCUMENTATION",
        "MISSING_DOCUMENT_LIMITS",
        "CONTEXT_READY",
    ]
    
class EscalationResponse(BaseModel):
    incident: Incident
    status: Literal["manual_escalation_required"]
    reason: str

@app.get("/health")
def health():
    return {"service": "ai-app", "status": "ok"} 

@app.post(
    "/investigate/{incident_id}",
    response_model=InvestigationContext | EscalationResponse,
)
async def investigate(incident_id: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            incident_response = await client.get(
                f"{MOCK_SERVICES_URL}/incidents/{incident_id}"
            )

            if incident_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Incident not found",
                )

            incident_response.raise_for_status()
            incident_data = incident_response.json()

            if incident_data["priority"] == "P1":
                return {
                    "incident": incident_data,
                    "status": "manual_escalation_required",
                    "reason": (
                        "Incidente P1 exige tratamento humano; "
                        "investigação automática interrompida."
                    ),
                }

            application = incident_data["application"]

            monitoring_response = await client.get(
                f"{MOCK_SERVICES_URL}/monitoring/{application}"
            )

            if monitoring_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Monitoring data not found",
                )

            monitoring_response.raise_for_status()
            monitoring_data = monitoring_response.json()

            logs_response = await client.get(
                f"{MOCK_SERVICES_URL}/logs/{application}"
            )

            if logs_response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Logs not found",
                )

            logs_response.raise_for_status()
            logs_data = logs_response.json()

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Mock Services não respondeu dentro do tempo limite",
        ) from exc

    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail="Falha na conexão com Mock Services",
        ) from exc

    query = (
        f'Aplicação: {incident_data["application"]}. '
        f'Incidente: {incident_data["summary"]}. '
        + " ".join(entry["message"] for entry in logs_data["entries"])
    )

    try:
        documentation = await run_in_threadpool(search_chunks, query)

        document_ids = {
            result["chunk"]["document_id"]
            for result in documentation
        }

        document_limits = []

        for document_id in sorted(document_ids):
            limits = await run_in_threadpool(
                get_document_limits,
                document_id,
            )
            document_limits.extend(limits)

    except ResponseHandlingException as exc:
        raise HTTPException(
            status_code=503,
            detail="Falha na comunicação com a base documental",
        ) from exc

    documentation_status = (
        "retrieved" if documentation else "no_matches"
    )

    retrieved_document_ids = {
        item["chunk"]["document_id"] 
        for item in documentation
    }

    limits_document_ids = {
        chunk["document_id"] 
        for chunk in document_limits
    }

    missing_limits = retrieved_document_ids - limits_document_ids

    decision = evaluate_context(documentation, document_limits)

    return {
        "incident": incident_data,
        "monitoring": monitoring_data,
        "logs": logs_data,
        "documentation": documentation,
        "document_limits": document_limits,
        "documentation_status": documentation_status,
        "analysis_status": decision["analysis_status"],
        "analysis_reason": decision["analysis_reason"],
        "analysis_code": decision["analysis_code"],
    }