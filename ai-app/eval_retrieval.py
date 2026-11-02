import json
from pathlib import Path
from eval_common import evaluate_expected_ids, print_summary


CASES_PATH = Path(__file__).resolve().parent.parent / "evals" / "retrieval_cases.json"


def load_cases(path):
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("Os casos devem formar uma lista não vazia")
    fields = {"case_id", "query", "expected_chunk_ids", "expected_behavior", "reason"}
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != fields:
            raise ValueError("Campos de caso inválidos")
        for field in fields - {"expected_chunk_ids"}:
            if not isinstance(case[field], str) or not case[field].strip():
                raise ValueError(f"Campo inválido: {field}")
        if case["case_id"] in seen:
            raise ValueError(f"case_id duplicado: {case['case_id']}")
        seen.add(case["case_id"])
        ids = case["expected_chunk_ids"]
        if (
            not isinstance(ids, list)
            or any(not isinstance(value, str) or not value.strip() for value in ids)
            or len(ids) != len(set(ids))
        ):
            raise ValueError("expected_chunk_ids inválidos")
        behavior = case["expected_behavior"]
        if behavior not in ("retrieve", "abstain"):
            raise ValueError("expected_behavior inválido")
        if (behavior == "retrieve" and not ids) or (behavior == "abstain" and ids):
            raise ValueError("IDs esperados incompatíveis com expected_behavior")
    return cases


def load_search():
    # Importar somente após validar os casos: este módulo carrega o modelo.
    from search_qdrant import search_chunks

    return search_chunks


def evaluate_case(case, results):
    returned_ids = {result["chunk"]["chunk_id"] for result in results}
    return evaluate_expected_ids(case, returned_ids)


def run_cases(cases, search):
    approved = failed = errors = 0
    for case in cases:
        print(f"\n{case['case_id']}")
        print(f"Esperados: {json.dumps(case['expected_chunk_ids'], ensure_ascii=False)}")
        try:
            results = search(case["query"], top_k=3, min_similarity=0.50)
            passed = evaluate_case(case, results)
            returned = [
                f"  {result['chunk']['chunk_id']} — score={result['score']:.6f}"
                for result in results
            ]
        except Exception as exc:
            # Erros não são convertidos em resultados vazios nem em reprovações.
            errors += 1
            print(f"ERRO DE EXECUÇÃO — {type(exc).__name__}: {exc}")
            print("Retornados: indisponíveis; expectativa não avaliada.")
            continue
        if passed:
            approved += 1
            print("APROVADO")
        else:
            failed += 1
            print("FALHOU")
        print("Retornados:" if returned else "Retornados: []")
        for line in returned:
            print(line)
    return print_summary(approved, failed, errors, len(cases))


def main(cases_path=CASES_PATH):
    try:
        cases = load_cases(cases_path)
        search = load_search()
    except Exception as exc:
        print(f"ERRO GLOBAL — {type(exc).__name__}: {exc}")
        print("Consultas não iniciadas; expectativas não avaliadas.")
        return 2
    return run_cases(cases, search)


if __name__ == "__main__":
    raise SystemExit(main())
