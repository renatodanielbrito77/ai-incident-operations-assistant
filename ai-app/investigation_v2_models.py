"""Contratos V2 sem importar API, cliente, embeddings ou audit."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from document_policy import ClassifiedContext, ClassifiedPackage
from investigation_models import (
    Incident, Monitoring, LogEntry, ApplicationLogs, HistoricalIncident, HistoricalIncidentMatch,
)
from recommendation_models import NonBlankText
from temporal_rules import assess_temporal, parse_timestamp, validate_window


class EvidenceConfig(BaseModel):
    # Extras são dados preservados, não campos descartados nem regras interpretadas.
    model_config = ConfigDict(strict=True, extra="allow")
    __pydantic_extra__: dict[str, JsonValue] = Field(init=False)


class IncidentV2(Incident, EvidenceConfig):
    window_start: str
    window_end: str

    @model_validator(mode="after")
    def window(self):
        validate_window(self.window_start, self.window_end)
        return self


class MonitoringV2(Monitoring, EvidenceConfig):
    error_rate_percent: int | float
    latency_p95_ms: int | float
    timestamp: str

    @field_validator("timestamp")
    @classmethod
    def timestamp_valid(cls, value):
        parse_timestamp(value)
        return value


class LogEntryV2(LogEntry, EvidenceConfig):
    @field_validator("timestamp")
    @classmethod
    def timestamp_valid(cls, value):
        parse_timestamp(value)
        return value


class ApplicationLogsV2(ApplicationLogs, EvidenceConfig):
    entries: list[LogEntryV2]


class HistoricalIncidentV2(HistoricalIncident, EvidenceConfig):
    occurred_at: str
    record_completeness_declared: NonBlankText
    fictional: Literal[True]

    @field_validator("occurred_at")
    @classmethod
    def timestamp_valid(cls, value):
        parse_timestamp(value)
        return value


class HistoricalMatchV2(HistoricalIncidentMatch):
    model_config = ConfigDict(strict=True, extra="forbid")
    historical_incident: HistoricalIncidentV2


class EvidenceSnapshotV2(EvidenceConfig):
    fictional: Literal[True]
    incident: IncidentV2
    monitoring: MonitoringV2
    logs: ApplicationLogsV2
    additional_sources_provided: list[JsonValue]

    @model_validator(mode="after")
    def applications(self):
        if self.incident.application != self.monitoring.application or self.incident.application != self.logs.application:
            raise ValueError("Aplicações do recorte não correspondem")
        return self


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class LogApplicability(StrictModel):
    entry_index: Annotated[int, Field(ge=0)]
    temporal_status: Literal["within_window", "outside_window"]
    message_status: Literal["filled", "blank"]


class TemporalAssessment(StrictModel):
    window_start: str
    window_end: str
    monitoring_timestamp: str
    monitoring_applicability: Literal["within_window", "outside_window"]
    log_applicability: list[LogApplicability]
    log_status: Literal["usable", "NO_LOG_MESSAGE", "LOGS_OUTSIDE_WINDOW"]


class InvestigationContextV2(ClassifiedContext):
    investigation_schema_version: Literal["2.0"]
    incident: IncidentV2
    monitoring: MonitoringV2
    logs: ApplicationLogsV2
    historical_incidents: list[HistoricalIncidentV2]
    historical_incident_matches: list[HistoricalMatchV2]
    source_snapshot: EvidenceSnapshotV2
    temporal_assessment: TemporalAssessment
    applicable_log_entries: list[LogEntryV2]

    @model_validator(mode="after")
    def applicable_evidence(self):
        raw = self.source_snapshot.model_dump()
        if any(getattr(self, key).model_dump() != raw[key] for key in ("incident", "monitoring", "logs")):
            raise ValueError("Contexto alterou as evidências originais")
        expected = assess_temporal(raw["incident"], raw["monitoring"], raw["logs"]["entries"])
        if self.temporal_assessment.model_dump() != expected["assessment"]:
            raise ValueError("Avaliação temporal inconsistente com as evidências")
        if [e.model_dump() for e in self.applicable_log_entries] != expected["applicable_log_entries"]:
            raise ValueError("Logs aplicáveis divergentes das evidências")
        if self.temporal_assessment.log_status != "usable" or self.temporal_assessment.monitoring_applicability != "within_window":
            raise ValueError("Contexto documental exige logs e métricas aplicáveis")
        # A comparação não pode citar um sintoma encontrado apenas em log antigo.
        from history_rules import match_historical_incidents
        expected_matches = match_historical_incidents(
            [h.model_dump() for h in self.historical_incidents], expected["applicable_log_entries"]
        )
        if [m.model_dump() for m in self.historical_incident_matches] != expected_matches:
            raise ValueError("Correspondências históricas divergentes dos logs aplicáveis")
        return self


class InvestigationPackageV2(ClassifiedPackage):
    investigation_schema_version: Literal["2.0"] = "2.0"
    evidence: InvestigationContextV2


OutputState = Literal[
    "P1_MANUAL_ESCALATION", "NO_LOG_MESSAGE", "LOGS_OUTSIDE_WINDOW", "MONITORING_OUTSIDE_WINDOW",
    "CONTEXT_READY", "NO_DOCUMENTATION", "MISSING_DOCUMENT_LIMITS", "CONTRACT_ERROR",
    "DOCUMENT_INTEGRITY_ERROR", "DOCUMENT_CONTROL_ERROR", "OPERATIONAL_ERROR",
]


class HandoffV2(StrictModel):
    recipient: str
    channel: str
    channel_address: None = None  # Não informado, não inventar link.
    performed_by: Literal["analyst"] = "analyst"
    notification_sent: Literal[False] = False


class ErrorV2(StrictModel):
    error_type: str
    message: str


class InvestigationResultV2(StrictModel):
    state: OutputState
    stage: str
    audit_event_id: NonBlankText
    incident: IncidentV2 | None = None
    evidence: EvidenceSnapshotV2 | None = None
    temporal_assessment: TemporalAssessment | None = None
    historical_incidents: list[HistoricalIncidentV2] = Field(default_factory=list)
    historical_incident_matches: list[HistoricalMatchV2] = Field(default_factory=list)
    requested_data: list[str] = Field(default_factory=list)
    handoff: HandoffV2 | None = None
    context: InvestigationContextV2 | None = None
    package: InvestigationPackageV2 | None = None
    error: ErrorV2 | None = None
    candidate_produced: Literal[False] = False

    @model_validator(mode="after")
    def coherent(self):
        if self.state == "CONTEXT_READY":
            if self.package is None or self.context is None:
                raise ValueError("Contexto pronto exige pacote e contexto")
            if self.package.evidence != self.context or self.audit_event_id != self.package.audit_event_id:
                raise ValueError("Pacote/contexto/identificador divergentes")
        elif self.package is not None:
            raise ValueError("Encerramento não elegível/erro não produz pacote")
        if self.state == "P1_MANUAL_ESCALATION":
            if self.incident is None or self.incident.priority != "P1" or self.handoff is None:
                raise ValueError("Encaminhamento P1 inconsistente")
            if self.evidence is not None or self.context is not None or self.temporal_assessment is not None:
                raise ValueError("P1 não deve coletar evidências ou contexto")
        if self.state.endswith("ERROR") and self.error is None:
            raise ValueError("Erro exige descrição")
        return self
