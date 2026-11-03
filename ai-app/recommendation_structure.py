from recommendation_rules import validate_candidate_action, validate_candidate_references


def check_candidate_structure(
    candidate: dict,
    documentation: list[dict],
    document_limits: list[dict],
) -> dict:
    """Compõe verificações estruturais, sem avaliar sustentação semântica.

    Mesmo structural_checks_passed=True não autoriza execução nem comprova
    coerência entre texto, tipo de ação e conteúdo das referências.
    """
    references = validate_candidate_references(candidate, documentation, document_limits)
    action = validate_candidate_action(candidate)
    return {
        "references": references,
        "action": action,
        "structural_checks_passed": references["accepted"] and action["allowed"],
        "semantic_support_status": "not_evaluated",
    }
