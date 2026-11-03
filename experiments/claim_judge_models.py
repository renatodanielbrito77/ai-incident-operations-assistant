"""Contratos experimentais de julgamento; não aprovam candidatas ou ações."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(min_length=1, pattern=r'\S')]
StatementType = Literal['current_fact', 'historical_fact', 'suggestion']
Classification = Literal['sustentado', 'impreciso', 'não sustentado']


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')


class EvidenceItem(StrictModel):
    source_type: Literal['monitoring', 'current_logs', 'runbook', 'historical_incident']
    source_id: Text
    value: JsonValue


class EvidenceReference(StrictModel):
    source_id: Text
    json_pointer: Text


class ClaimJudgment(StrictModel):
    example_id: Text
    statement_type: StatementType
    assessment_status: Literal['evaluated', 'abstained']
    classification: Classification | None
    reason: Text
    evidence_references: list[EvidenceReference]

    @model_validator(mode='after')
    def check_consistency(self) -> Self:
        if (self.assessment_status == 'evaluated') != (self.classification is not None):
            raise ValueError('Classificação obrigatória apenas em evaluated; abstained exige null')
        if self.assessment_status == 'evaluated' and not self.evidence_references:
            raise ValueError('Julgamento exige referência à evidência efetivamente enviada')
        pairs = [(r.source_id, r.json_pointer) for r in self.evidence_references]
        if len(pairs) != len(set(pairs)):
            raise ValueError('Referências duplicadas')
        return self


class TextSpan(StrictModel):
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]


class JudgeInput(StrictModel):
    example_id: Text
    source_run_id: Text
    source_model: Text
    audit_event_id: Text
    statement_fragment: Text
    statement_type: StatementType
    candidate_text_span: TextSpan
    candidate_context: dict
    candidate_cited_chunk_ids: list[Text]
    evidence_scope: Literal['selected_evidence_only_not_complete_context']
    evidence: list[EvidenceItem]
