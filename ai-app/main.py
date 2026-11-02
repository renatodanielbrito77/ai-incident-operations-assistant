from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from search_qdrant import search_chunks, get_document_limits
from starlette.concurrency import run_in_threadpool
from qdrant_client.http.exceptions import ResponseHandlingException
from context_rules import evaluate_context
from history_rules import match_historical_incidents
from typing import Literal
from audit import build_audit_event, append_audit_event
from pathlib import Path

app = FastAPI()
MOCK_SERVICES_URL = os.getenv("MOCK_SERVICES_URL", "http://localhost:8001")
AUDIT_PATH = Path(os.getenv("AUDIT_PATH", "/app/audit/events.jsonl"))

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

class HistoricalIncident(BaseModel):
    historical_incident_id: str
    application: str
    summary: str
    symptoms: list[str]
    resolution: str
    observed_result: str

class HistoricalIncidentMatch(BaseModel):
    historical_incident: HistoricalIncident
    matched_symptoms: list[str]

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
    audit_event_id: str
    incident: Incident
    monitoring: Monitoring
    logs: ApplicationLogs
    historical_incidents: list[HistoricalIncident]
    historical_incident_matches: list[HistoricalIncidentMatch]
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
    audit_event_id: str
    incident: Incident
    status: Literal["manual_escalation_required"]
    reason: str


async def persist_audit_event(event: dict):
    try:
        await run_in_threadpool(
            append_audit_event,
            event,
            AUDIT_PATH,
        )
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível registrar a investigação no audit",
        ) from exc

@app.get("/health")
def health():
    return {"service": "ai-app", "status": "ok"} 

@app.post(
    "/investigate/{incident_id}",
    response_model=InvestigationContext | EscalationResponse,
)
async def investigate(incident_id: str):

    stage = "incident_lookup"
    historical_incident_ids = []
    matched_historical_incident_ids = []
    historical_matching_status = "not_evaluated"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            incident_response = await client.get(
                f"{MOCK_SERVICES_URL}/incidents/{incident_id}"
            )

            if incident_response.status_code == 404:
                audit_event = build_audit_event(
                    incident_id=incident_id,
                    analysis_code="INCIDENT_NOT_FOUND",
                    retrieved_chunk_ids=[],
                    limit_chunk_ids=[],
                    stage="incident_lookup",
                )

                await persist_audit_event(audit_event)

                raise HTTPException(
                    status_code=404,
                    detail="Incident not found",
                )

            incident_response.raise_for_status()
            incident_data = incident_response.json()

            if incident_data["priority"] == "P1":

                audit_event = build_audit_event(
                    incident_id=incident_data["incident_id"],
                    analysis_code="P1_MANUAL_ESCALATION",
                    retrieved_chunk_ids=[],
                    limit_chunk_ids=[],
                    stage="priority_check",
                )

                await persist_audit_event(audit_event)

                return {
                    "audit_event_id": audit_event["event_id"],
                    "incident": incident_data,
                    "status": "manual_escalation_required",
                    "reason": (
                        "Incidente P1 exige tratamento humano; "
                        "investigação automática interrompida."
                    ),
                }

            application = incident_data["application"]

            stage = "historical_incidents_lookup"
            historical_response = await client.get(
                f"{MOCK_SERVICES_URL}/historical-incidents",
                params={"application": application},
            )
            historical_response.raise_for_status()
            historical_incidents = historical_response.json()["historical_incidents"]
            historical_incident_ids = [
                incident["historical_incident_id"] for incident in historical_incidents
            ]

            stage = "monitoring_lookup"
            
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

            stage = "logs_lookup"

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
        audit_event = build_audit_event(
            incident_id=incident_id,
            analysis_code="MOCK_SERVICES_TIMEOUT",
            retrieved_chunk_ids=[],
            limit_chunk_ids=[],
            stage=stage,
            historical_incident_ids=historical_incident_ids,
        )

        await persist_audit_event(audit_event)

        raise HTTPException(
            status_code=504,
            detail="Mock Services não respondeu dentro do tempo limite",
        ) from exc

    except httpx.ConnectError as exc:
        audit_event = build_audit_event(
            incident_id=incident_id,
            analysis_code="MOCK_SERVICES_CONNECTION_FAILED",
            retrieved_chunk_ids=[],
            limit_chunk_ids=[],
            stage=stage,
            historical_incident_ids=historical_incident_ids,
        )

        await persist_audit_event(audit_event)

        raise HTTPException(
            status_code=503,
            detail="Falha na conexão com Mock Services",
        ) from exc

    historical_incident_matches = match_historical_incidents(
        historical_incidents, logs_data["entries"]
    )
    matched_historical_incident_ids = [
        match["historical_incident"]["historical_incident_id"]
        for match in historical_incident_matches
    ]
    historical_matching_status = "evaluated"

    query = (
        f'Aplicação: {incident_data["application"]}. '
        f'Incidente: {incident_data["summary"]}. '
        + " ".join(entry["message"] for entry in logs_data["entries"])
    )

    try:
        stage = "documentation_search"
        documentation = await run_in_threadpool(search_chunks, query)

        document_ids = {
            result["chunk"]["document_id"]
            for result in documentation
        }

        document_limits = []

        for document_id in sorted(document_ids):
            stage = "document_limits_lookup"
            limits = await run_in_threadpool(
                get_document_limits,
                document_id,
            )
            document_limits.extend(limits)

    except ResponseHandlingException as exc:
        audit_event = build_audit_event(
            incident_id=incident_id,
            analysis_code="DOCUMENT_BASE_COMMUNICATION_FAILED",
            retrieved_chunk_ids=[],
            limit_chunk_ids=[],
            stage=stage,
            historical_incident_ids=historical_incident_ids,
            matched_historical_incident_ids=matched_historical_incident_ids,
            historical_matching_status=historical_matching_status,
        )

        await persist_audit_event(audit_event)

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

    audit_event = build_audit_event(
        incident_id=incident_data["incident_id"],
        analysis_code=decision["analysis_code"],
        stage="context_evaluation",
        historical_incident_ids=historical_incident_ids,
        matched_historical_incident_ids=matched_historical_incident_ids,
        historical_matching_status=historical_matching_status,
        retrieved_chunk_ids=[
            item["chunk"]["chunk_id"] 
            for item in documentation
        ],
        limit_chunk_ids=[
            chunk["chunk_id"]
            for chunk in document_limits
        ],
    )

    await persist_audit_event(audit_event)

    return {
        "audit_event_id": audit_event["event_id"],
        "incident": incident_data,
        "monitoring": monitoring_data,
        "logs": logs_data,
        "historical_incidents": historical_incidents,
        "historical_incident_matches": historical_incident_matches,
        "documentation": documentation,
        "document_limits": document_limits,
        "documentation_status": documentation_status,
        "analysis_status": decision["analysis_status"],
        "analysis_reason": decision["analysis_reason"],
        "analysis_code": decision["analysis_code"],
    }