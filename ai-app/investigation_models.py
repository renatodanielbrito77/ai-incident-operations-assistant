"""Contratos de investigação compartilhados, sem dependências de execução."""

from typing import Literal

from pydantic import BaseModel


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

class MissingLogMessageResponse(BaseModel):
    audit_event_id: str
    incident: Incident
    status: Literal["additional_data_required"]
    analysis_code: Literal["NO_LOG_MESSAGE"]
    reason: str
    requested_data: list[str]
