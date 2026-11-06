"""Documentos classificados: contratos e regra de elegibilidade sem rede/modelo."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from investigation_models import RunbookChunk, RetrievedDocument
from llm_input_models import ReadyInvestigationContext, LLMInputPackage


class DocumentIntegrityError(ValueError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Classification(StrictModel):
    document_id: str = Field(min_length=1)
    document_version: str = Field(min_length=1)
    document_status: Literal["active", "deprecated", "unconfirmed"]
    classification_revision: int = Field(ge=1)
    classified_by: str = Field(min_length=1)
    chunk_ids: list[str] = Field(min_length=1)
    payload_hashes: dict[str, str]

    @model_validator(mode="after")
    def complete(self):
        if any(not v.strip() for v in (self.document_id, self.document_version, self.classified_by)):
            raise ValueError("Identificação/classificação em branco")
        if len(set(self.chunk_ids)) != len(self.chunk_ids) or set(self.chunk_ids) != set(self.payload_hashes):
            raise ValueError("Inventário de chunks incompleto/duplicado")
        return self


class ClassifiedChunk(RunbookChunk):
    model_config = ConfigDict(strict=True, extra="forbid")
    document_version: str = Field(min_length=1)
    document_status: Literal["active", "deprecated", "unconfirmed"]
    classification_revision: int = Field(ge=1)
    classified_by: str = Field(min_length=1)
    review_date: str | None  # None = não informado, nunca inferir pela idade.


class ClassifiedResult(RetrievedDocument):
    model_config = ConfigDict(strict=True, extra="forbid")
    chunk: ClassifiedChunk


class ClassifiedContext(ReadyInvestigationContext):
    documentation: list[ClassifiedResult]
    document_limits: list[ClassifiedChunk]


class ClassifiedPackage(LLMInputPackage):
    evidence: ClassifiedContext
    document_policy_version: Literal["1.0"] = "1.0"


def payload_hash(chunk):
    """Identidade do conteúdo/metadados, exceto decisão de classificação mutável."""
    import hashlib
    import json
    raw = chunk.model_dump() if isinstance(chunk, BaseModel) else dict(chunk)
    for key in ("document_status", "classification_revision", "classified_by"):
        raw.pop(key, None)
    return hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def eligible(chunk: dict | ClassifiedChunk, records: list[Classification]) -> bool:
    """Única regra: divergência é erro; inelegibilidade consistente retorna False."""
    try:
        value = chunk if isinstance(chunk, ClassifiedChunk) else ClassifiedChunk.model_validate(chunk)
    except ValueError as exc:
        raise DocumentIntegrityError("Payload documental inválido") from exc
    matches = [r for r in records if (r.document_id, r.document_version) ==
               (value.document_id, value.document_version)]
    if len(matches) != 1:
        raise DocumentIntegrityError("Versão não corresponde ao catálogo")
    record = matches[0]
    if (value.document_status, value.classification_revision, value.classified_by) != (
        record.document_status, record.classification_revision, record.classified_by
    ) or value.chunk_id not in record.chunk_ids or payload_hash(value) != record.payload_hashes[value.chunk_id]:
        raise DocumentIntegrityError("Payload diverge da classificação/conteúdo persistidos")
    return record.document_status == "active"
