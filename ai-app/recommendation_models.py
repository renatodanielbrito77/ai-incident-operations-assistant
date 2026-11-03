"""Contratos estruturais; não avaliam sustentação semântica ou execução."""

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, model_validator


def _require_nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("O texto deve conter algum caractere além de espaços")
    return value


NonBlankText = Annotated[str, AfterValidator(_require_nonblank)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class RecommendationCandidate(_StrictModel):
    text: NonBlankText
    # Valores desconhecidos são rejeitados pela política, não pelo contrato.
    action_type: str
    cited_chunk_ids: list[NonBlankText]


class ReferenceValidationResult(_StrictModel):
    """accepted refere-se somente à presença das referências no contexto."""

    accepted: bool
    validation_code: Literal[
        "REFERENCES_IN_CONTEXT", "REFERENCES_OUTSIDE_CONTEXT", "NO_REFERENCES"
    ]
    invalid_chunk_ids: list[NonBlankText]

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if self.accepted != (self.validation_code == "REFERENCES_IN_CONTEXT"):
            raise ValueError("accepted incompatível com validation_code")
        if bool(self.invalid_chunk_ids) != (self.validation_code == "REFERENCES_OUTSIDE_CONTEXT"):
            raise ValueError("invalid_chunk_ids incompatível com validation_code")
        return self


class ActionValidationResult(_StrictModel):
    allowed: bool
    validation_code: Literal[
        "ACTION_TYPE_ALLOWED", "ACTION_TYPE_FORBIDDEN", "UNKNOWN_ACTION_TYPE"
    ]

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if self.allowed != (self.validation_code == "ACTION_TYPE_ALLOWED"):
            raise ValueError("allowed incompatível com validation_code")
        return self


class CandidateStructureReport(_StrictModel):
    """Passagem estrutural não autoriza execução nem comprova suporte do texto."""

    references: ReferenceValidationResult
    action: ActionValidationResult
    structural_checks_passed: bool
    semantic_support_status: Literal["not_evaluated"]

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if self.structural_checks_passed != (self.references.accepted and self.action.allowed):
            raise ValueError("structural_checks_passed incompatível com os resultados separados")
        return self
