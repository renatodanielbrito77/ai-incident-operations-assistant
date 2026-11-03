"""Avalia expectativas estruturais; anotações humanas não são avaliação automática."""

import json
from pathlib import Path

from recommendation_models import RecommendationCandidate, CandidateStructureReport
from recommendation_structure import check_candidate_structure


ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "evals" / "candidate_cases.json"
CHUNKS_PATH = ROOT / "data" / "chunks.json"
HUMAN_LABELS = {
    "compatible": "compatível",
    "contradicts": "contradiz",
    "not_verifiable_in_context": "sem suporte verificável no contexto",
}


def index_unique(records, id_field):
    if not isinstance(records, list):
        raise ValueError(f"{id_field}: esperada uma lista")
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{id_field}: registro deve ser objeto")
        value = record.get(id_field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{id_field}: identificador ausente ou inválido")
        if value in indexed:
            raise ValueError(f"{id_field} duplicado: {value}")
        indexed[value] = record
    return indexed


def load_inputs(cases_path, chunks_path):
    data = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"contexts", "cases"}:
        raise ValueError("O conjunto deve conter contexts e cases")
    contexts = index_unique(data["contexts"], "context_id")
    cases = index_unique(data["cases"], "case_id")
    if not cases:
        raise ValueError("O conjunto deve conter ao menos um caso")
    chunks = index_unique(
        json.loads(Path(chunks_path).read_text(encoding="utf-8")), "chunk_id"
    )
    return list(cases.values()), contexts, chunks


def build_context(context, chunks):
    groups = []
    for field in ("documentation_chunk_ids", "document_limit_chunk_ids"):
        ids = context[field]
        if not isinstance(ids, list) or any(not isinstance(value, str) or not value.strip() for value in ids):
            raise ValueError(f"{field}: esperada lista de IDs preenchidos")
        selected = []
        for chunk_id in ids:
            if chunk_id not in chunks:
                raise ValueError(f"Chunk declarado no contexto não encontrado: {chunk_id}")
            selected.append(chunks[chunk_id])
        groups.append(selected)
    return [{"chunk": chunk} for chunk in groups[0]], groups[1]


def run_cases(cases, contexts, chunks):
    matched = mismatched = errors = 0
    for case in cases:
        case_id = case["case_id"]
        try:
            context_id = case["context_id"]
            if not isinstance(context_id, str) or context_id not in contexts:
                raise ValueError(f"Contexto referenciado inexistente: {context_id}")
            candidate = RecommendationCandidate.model_validate(case["candidate"])
            expected = CandidateStructureReport.model_validate(case["expected_structure"])
            annotation = case["human_semantic_annotation"]
            if not isinstance(annotation, dict) or set(annotation) != {"assessment", "reason"}:
                raise ValueError("Anotação humana inválida")
            assessment = annotation["assessment"]
            if not isinstance(assessment, str) or assessment not in HUMAN_LABELS:
                raise ValueError("Classificação humana desconhecida")
            if not isinstance(annotation["reason"], str) or not annotation["reason"].strip():
                raise ValueError("Justificativa humana ausente")
            documentation, limits = build_context(contexts[context_id], chunks)
            report = CandidateStructureReport.model_validate(check_candidate_structure(
                candidate.model_dump(), documentation, limits
            ))
        except Exception as exc:
            errors += 1
            print(f"\n{case_id} — ERRO DE EXECUÇÃO POR CASO — {type(exc).__name__}: {exc}")
            print("Expectativa não avaliada; nenhum resultado estrutural fabricado.")
            continue
        observed = report.model_dump()
        expected_data = expected.model_dump()
        same = observed == expected_data
        matched += same
        mismatched += not same
        outcome = "atendida" if same else "NÃO ATENDIDA"
        print(f"\n{case_id} — expectativa estrutural {outcome}; anotação humana: {HUMAN_LABELS[assessment]}")
        print("Resultado estrutural: verificações " + (
            "passaram" if report.structural_checks_passed else "reprovadas"
        ))
        print("Relatório observado: " + json.dumps(observed, ensure_ascii=False))
        if not same:
            print("Relatório esperado: " + json.dumps(expected_data, ensure_ascii=False))
            print("Campos divergentes: " + ", ".join(
                key for key in expected_data if observed[key] != expected_data[key]
            ))
        print(f"Sustentação semântica automatizada: {report.semantic_support_status}")
        print("Justificativa humana: " + annotation["reason"])
        print("Expectativa atendida não significa aprovação da candidata.")
    print(f"\nExpectativas estruturais atendidas: {matched}/{len(cases)}")
    print(f"Expectativas estruturais não atendidas: {mismatched}")
    print(f"Erros de execução: {errors}")
    print("Anotações humanas: exibidas, não avaliadas automaticamente.")
    return 2 if errors else 1 if mismatched else 0


def main(cases_path=CASES_PATH, chunks_path=CHUNKS_PATH):
    try:
        cases, contexts, chunks = load_inputs(cases_path, chunks_path)
    except Exception as exc:
        print(f"ERRO GLOBAL — {type(exc).__name__}: {exc}")
        print("Não foi possível interpretar o conjunto; casos não executados.")
        return 2
    return run_cases(cases, contexts, chunks)


if __name__ == "__main__":
    raise SystemExit(main())
