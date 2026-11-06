"""Fluxo V2 com dependências injetadas; nenhuma API, rede ou modelo na importação."""
from pydantic import ValidationError

from context_rules import evaluate_context
from document_collection import ControlError
from document_policy import DocumentIntegrityError
from history_rules import match_historical_incidents
from investigation_v2_models import (
    EvidenceSnapshotV2, HistoricalIncidentV2, HandoffV2, IncidentV2,
    InvestigationContextV2, InvestigationResultV2,
)
from temporal_rules import assess_temporal


def investigate_v2(incident_data, *, evidence_provider, history_provider,
                   document_control_factory, encode_query, audit_event_id):
    """Somente o caminho documental elegível abre controle/lock/conexão."""
    incident = snapshot = temporal = None
    histories, matches = [], []
    stage = "incident_contract"

    def result(state, **kwargs):
        return InvestigationResultV2(
            state=state, stage=stage, audit_event_id=audit_event_id, incident=incident,
            evidence=snapshot, temporal_assessment=temporal,
            historical_incidents=histories, historical_incident_matches=matches, **kwargs,
        )

    try:
        incident = IncidentV2.model_validate(incident_data)
        stage = "priority_check"
        if incident.priority == "P1":
            return result("P1_MANUAL_ESCALATION", handoff=HandoffV2(
                recipient="Responsável de plantão de Operações",
                channel="Canal corporativo de incidentes críticos",
            ))

        stage = "evidence_contract"
        snapshot = EvidenceSnapshotV2.model_validate(evidence_provider())
        if snapshot.incident != incident:
            raise ValueError("Incidente das evidências difere do incidente recebido")
        data = snapshot.model_dump()
        evaluated = assess_temporal(data["incident"], data["monitoring"], data["logs"]["entries"])
        temporal = evaluated["assessment"]
        applicable_logs = evaluated["applicable_log_entries"]
        stage = "log_evidence_check"
        if temporal["log_status"] == "NO_LOG_MESSAGE":
            return result("NO_LOG_MESSAGE", requested_data=[
                "Mensagem de log observada, com timestamp e fuso, na janela original do incidente."
            ])
        if temporal["log_status"] == "LOGS_OUTSIDE_WINDOW":
            return result("LOGS_OUTSIDE_WINDOW", requested_data=[
                f"Logs com mensagem na janela original {incident.window_start} até {incident.window_end}; não ampliar automaticamente."
            ])
        stage = "monitoring_evidence_check"
        if temporal["monitoring_applicability"] == "outside_window":
            return result("MONITORING_OUTSIDE_WINDOW", requested_data=[
                f"Métricas da janela original {incident.window_start} até {incident.window_end}; as recebidas não se aplicam ao período atual."
            ])

        stage = "history_contract"
        histories = [HistoricalIncidentV2.model_validate(h) for h in history_provider(incident.application)]
        if any(h.application != incident.application for h in histories):
            raise ValueError("Histórico fornecido pertence a outra aplicação")
        historical_data = [h.model_dump() for h in histories]
        matches = match_historical_incidents(historical_data, applicable_logs)
        query = (
            f"Aplicação: {incident.application}. Incidente: {incident.summary}. "
            + " ".join(entry["message"] for entry in applicable_logs)
        )
        stage = "document_control"
        with document_control_factory() as control:
            stage = "documentation_search"
            documentation = control.search(encode_query(query))
            limits = []
            for document_id, version in sorted({
                (item["chunk"]["document_id"], item["chunk"]["document_version"])
                for item in documentation
            }):
                stage = "document_limits_lookup"
                limits.extend(control.limits(document_id, version))
            stage = "context_evaluation"
            decision = evaluate_context(documentation, limits)
            if decision["analysis_code"] != "CONTEXT_READY":
                return result(decision["analysis_code"])
            stage = "package_validation"
            context = InvestigationContextV2.model_validate(dict(
                investigation_schema_version="2.0", audit_event_id=audit_event_id,
                incident=data["incident"], monitoring=data["monitoring"], logs=data["logs"],
                historical_incidents=historical_data, historical_incident_matches=matches,
                documentation=documentation, document_limits=limits, documentation_status="retrieved",
                source_snapshot=data, temporal_assessment=temporal,
                applicable_log_entries=applicable_logs, **decision,
            ))
            package = control.package(context.model_dump())
            return result("CONTEXT_READY", context=context, package=package)
    except DocumentIntegrityError as exc:
        return result("DOCUMENT_INTEGRITY_ERROR", error=dict(error_type=type(exc).__name__, message=str(exc)))
    except ControlError as exc:
        return result("DOCUMENT_CONTROL_ERROR", error=dict(error_type=type(exc).__name__, message=str(exc)))
    except (ValidationError, ValueError) as exc:
        state = "CONTRACT_ERROR" if stage.endswith("contract") else "OPERATIONAL_ERROR"
        return result(state, error=dict(error_type=type(exc).__name__, message=str(exc)))
    except Exception as exc:
        # Falha operacional é registrada; nunca convertida em ausência documental.
        return result("OPERATIONAL_ERROR", error=dict(error_type=type(exc).__name__, message=str(exc)))
