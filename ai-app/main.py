from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from search_qdrant import search_chunks
from starlette.concurrency import run_in_threadpool

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

class RetrievedDocument(BaseModel):
    score: float
    chunk: dict

class InvestigationContext(BaseModel):
    incident: Incident
    monitoring: Monitoring
    logs: ApplicationLogs
    documentation: list[RetrievedDocument]

class EscalationResponse(BaseModel):
    incident: Incident
    status: str
    reason: str

@app.get("/health")
def health():
    return {"service": "ai-app", "status": "ok"} 

@app.post("/investigate/{incident_id}", 
          response_model=InvestigationContext | EscalationResponse,)

async def investigate(incident_id: str):

    try:
        async with httpx.AsyncClient() as client:
            incident_response = await client.get(
                f"{MOCK_SERVICES_URL}/incidents/{incident_id}",
                timeout=5.0,
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {exc}",
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Mock Services não respondeu dentro do tempo limite",
        ) from exc

    if incident_response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    incident_response.raise_for_status()
    incident_data = incident_response.json()
    application = incident_data["application"]

    if (incident_data["priority"] == "P1"):
        return {
            "incident": incident_data,
            "status": "manual_escalation_required",
            "reason": "Incidente P1 exige tratamento humano; investigação automática interrompida.",
        }

    try:
        async with httpx.AsyncClient() as client:
            monitoring_response = await client.get(
                f"{MOCK_SERVICES_URL}/monitoring/{application}",
                timeout=5.0,
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {exc}",
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Mock Services não respondeu dentro do tempo limite",
        ) from exc

    if monitoring_response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Monitoring data not found",
        )

    monitoring_response.raise_for_status()
    monitoring_data = monitoring_response.json()

    try:
        async with httpx.AsyncClient() as client:
            logs_response = await client.get(
                f"{MOCK_SERVICES_URL}/logs/{application}",
                timeout=5.0,
            )
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {exc}",
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Mock Services não respondeu dentro do tempo limite",
        ) from exc
            
    if logs_response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Logs not found",
        )

    logs_response.raise_for_status()
    logs_data = logs_response.json()

    query = (
        f'Aplicação: {incident_data["application"]}. '
        f'Incidente: {incident_data["summary"]}. '
        + " ".join(entry["message"] for entry in logs_data["entries"])
    )

    documentation = await run_in_threadpool(search_chunks, query)

    return {
        "incident": incident_data,
        "monitoring": monitoring_data,
        "logs": logs_data,
        "documentation": documentation,
    }
