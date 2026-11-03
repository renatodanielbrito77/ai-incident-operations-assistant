"""Apresentação Markdown pura, sem consultas ou execução de ações."""

from html import escape

from recommendation_models import RecommendationCandidate, CandidateStructureReport


def _literal(value: str) -> str:
    # <pre> mantém espaços e quebras; escape impede fechar o bloco ou injetar HTML.
    # Markdown dentro de um bloco HTML pre é texto, não título, link ou código ativo.
    return "<pre>" + escape(value, quote=True) + "</pre>"


def render_candidate_report(
    candidate: RecommendationCandidate,
    report: CandidateStructureReport,
    documentation: list[dict],
    document_limits: list[dict],
) -> str:
    """Renderiza somente os dados fornecidos; não avalia sustentação semântica.

    A candidata e o relatório devem pertencer à mesma avaliação e já estar
    validados. Nenhuma referência é buscada fora do contexto recebido.
    """
    passed = report.structural_checks_passed
    lines = [
        "# Candidata para revisão humana — verificações estruturais passaram"
        if passed else "# Candidata rejeitada nas verificações estruturais",
        "",
        "> Sustentação semântica não avaliada.",
        "> A presença das referências e a aceitação do tipo declarado não comprovam",
        "> que os trechos sustentam o texto nem autorizam execução.",
        "",
    ]
    if not passed:
        lines += [
            "> Não apresentar esta candidata como orientação a seguir.",
            "", "## Motivos da rejeição", "",
        ]
        if not report.references.accepted:
            lines.append(
                "- Nenhuma referência foi informada — NO_REFERENCES."
                if report.references.validation_code == "NO_REFERENCES"
                else "- Há referências fora do contexto fornecido — REFERENCES_OUTSIDE_CONTEXT."
            )
            if report.references.invalid_chunk_ids:
                lines += ["", "IDs rejeitados:", "",
                          _literal("\n".join(report.references.invalid_chunk_ids)), ""]
        if not report.action.allowed:
            lines.append(
                "- Tipo de ação declarado rejeitado pela política — ACTION_TYPE_FORBIDDEN."
                if report.action.validation_code == "ACTION_TYPE_FORBIDDEN"
                else "- Tipo de ação declarado desconhecido — UNKNOWN_ACTION_TYPE."
            )
        lines.append("")
    lines += [
        "## Conteúdo fornecido para avaliação", "", "Texto:", "",
        _literal(candidate.text), "", "Tipo de ação declarado:", "",
        _literal(candidate.action_type), "", "## Verificações", "",
        f"- Referências: {'aceitas' if report.references.accepted else 'rejeitadas'} — {report.references.validation_code}.",
        f"- Política do tipo declarado: {'permitido' if report.action.allowed else 'rejeitado'} — {report.action.validation_code}.",
        f"- Verificações estruturais: {'passaram' if passed else 'reprovadas'}.",
        f"- Sustentação semântica: {report.semantic_support_status}.",
        "", "## Chunks citados disponíveis no contexto", "",
    ]
    context = {}
    for chunk in [item["chunk"] for item in documentation] + document_limits:
        context.setdefault(chunk["chunk_id"], chunk)
    cited_ids = list(dict.fromkeys(candidate.cited_chunk_ids))
    if not cited_ids:
        lines += ["Nenhuma referência citada.", ""]
    for index, chunk_id in enumerate(cited_ids, 1):
        lines += [f"### Referência {index}", "", "ID:", "", _literal(chunk_id), ""]
        chunk = context.get(chunk_id)
        if chunk is None:
            lines += ["Não encontrada no contexto fornecido. Conteúdo e origem não disponíveis.", ""]
            continue
        for label, key in (("Origem", "source"), ("Seção", "section"), ("Subseção", "subsection")):
            value = chunk.get(key)
            if value is not None:
                lines += [f"{label}:", "", _literal(value), ""]
            elif key == "source":
                lines += ["Origem: não fornecida no contexto.", ""]
        if chunk.get("content") is not None:
            lines += ["Conteúdo integral fornecido:", "", _literal(chunk["content"]), ""]
        else:
            lines += ["Conteúdo não fornecido no contexto.", ""]
    lines += [
        "## Limitações", "",
        "- O texto não foi confrontado semanticamente com os chunks.",
        "- Não foi verificada contradição entre texto e tipo de ação declarado.",
        "- O relatório usa somente o contexto fornecido; referências ausentes não foram completadas.",
        "- O relatório não autoriza execução. Nenhuma ação foi executada.", "",
    ]
    return "\n".join(lines)
