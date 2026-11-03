"""Montagem pura e serialização: não importa API, embeddings, rede ou audit."""

import json

from pydantic import BaseModel

from investigation_models import (
    EscalationResponse, MissingLogMessageResponse, InvestigationContext,
)
from llm_input_models import (
    DIRECTIVES, LLMInstructions, LLMInputPackage, ReadyInvestigationContext,
    PackageReady, PackageNotEligible,
)
from recommendation_models import RecommendationCandidate


def build_llm_input_package(
    investigation: dict | InvestigationContext | EscalationResponse | MissingLogMessageResponse,
) -> PackageReady | PackageNotEligible:
    data = investigation.model_dump() if isinstance(investigation, BaseModel) else investigation
    if isinstance(data, dict) and data.get("status") == "manual_escalation_required":
        source = EscalationResponse.model_validate(data, strict=True)
        return PackageNotEligible(
            status="not_eligible", reason_code="P1",
            incident_id=source.incident.incident_id, audit_event_id=source.audit_event_id,
        )
    if isinstance(data, dict) and data.get("status") == "additional_data_required":
        source = MissingLogMessageResponse.model_validate(data, strict=True)
        return PackageNotEligible(
            status="not_eligible", reason_code="NO_LOG_MESSAGE",
            incident_id=source.incident.incident_id, audit_event_id=source.audit_event_id,
        )
    source = InvestigationContext.model_validate(data, strict=True)
    # Qualquer declaração de prontidão passa pela validação de consistência;
    # não é reclassificada silenciosamente como abstenção.
    if source.analysis_code == "CONTEXT_READY" or source.analysis_status == "context_ready":
        ready = ReadyInvestigationContext.model_validate(data, strict=True)
    else:
        return PackageNotEligible(
            status="not_eligible", reason_code="P1" if source.incident.priority == "P1" else "ABSTAINED",
            incident_id=source.incident.incident_id, audit_event_id=source.audit_event_id,
        )
    instructions = LLMInstructions(
        policy_version="1.0",
        allowed_action_types=["observe", "request_verification"],
        forbidden_action_types=["change_environment"],
        directives=list(DIRECTIVES),
        output_contract="RecommendationCandidate",
        output_json_schema=RecommendationCandidate.model_json_schema(),
        semantic_support_status="not_evaluated",
    )
    return PackageReady(status="ready", package=LLMInputPackage(
        schema_version="1.0", incident_id=ready.incident.incident_id,
        audit_event_id=ready.audit_event_id, instructions=instructions, evidence=ready,
    ))


def serialize_llm_input_package(package: LLMInputPackage) -> str:
    """JSON determinístico, UTF-8 representável, sem truncar ou gerar IDs."""
    validated = LLMInputPackage.model_validate(package.model_dump(), strict=True)
    return json.dumps(
        validated.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
        indent=2, allow_nan=False,
    )
