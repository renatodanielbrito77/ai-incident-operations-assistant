def validate_candidate_references(
    candidate: dict,
    documentation: list[dict],
    document_limits: list[dict],
) -> dict:
    """Valida somente se os IDs citados existem no contexto recebido.

    A candidata contém text (str) e cited_chunk_ids (list[str]). accepted=True
    significa referências aceitas, não recomendação aprovada para execução.
    Não avalia o texto, sua sustentação ou respeito às restrições do runbook.
    Pressupõe entradas no contrato atual e não as modifica.
    """
    cited_ids = candidate["cited_chunk_ids"]
    if not cited_ids:
        return {
            "accepted": False,
            "validation_code": "NO_REFERENCES",
            "invalid_chunk_ids": [],
        }

    available_ids = {
        item["chunk"]["chunk_id"] for item in documentation
    } | {item["chunk_id"] for item in document_limits}
    invalid_ids = list(dict.fromkeys(
        chunk_id for chunk_id in cited_ids if chunk_id not in available_ids
    ))
    return {
        "accepted": not invalid_ids,
        "validation_code": (
            "REFERENCES_OUTSIDE_CONTEXT" if invalid_ids else "REFERENCES_IN_CONTEXT"
        ),
        "invalid_chunk_ids": invalid_ids,
    }
