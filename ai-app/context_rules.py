def evaluate_context(documentation: list, document_limits: list):
    if not documentation:
        return {
            "analysis_status": "abstained",
            "analysis_reason": (
                "Nenhum trecho atingiu o limiar de recuperação; "
                "recomendação baseada em runbook não será gerada."
            ),
        }

    retrieved_document_ids = {
        item["chunk"]["document_id"]
        for item in documentation
    }

    limits_document_ids = {
        chunk["document_id"]
        for chunk in document_limits
    }

    missing_limits = retrieved_document_ids - limits_document_ids

    if missing_limits:
        return {
            "analysis_status": "abstained",
            "analysis_reason": (
                "Limites não encontrados para os documentos: "
                + ", ".join(sorted(missing_limits))
            ),
        }

    return {
        "analysis_status": "context_ready",
        "analysis_reason": (
            "Contexto coletado com documentação e limites recuperados; "
            "nenhuma recomendação foi gerada."
        ),
    }
