import json

from eval_common import evaluate_expected_ids, print_summary
from eval_retrieval import CASES_PATH, load_cases


def load_retrieval_functions():
    from search_qdrant import search_chunks, get_document_limits

    return search_chunks, get_document_limits


def run_cases(cases, search, get_limits):
    approved = failed = errors = 0
    for case in cases:
        print(f"\n{case['case_id']}")
        print(f"Esperados: {json.dumps(case['expected_chunk_ids'], ensure_ascii=False)}")
        try:
            results = search(case["query"], top_k=3, min_similarity=0.50)
            search_lines = [
                f"  {result['chunk']['chunk_id']} — score={result['score']:.6f}"
                for result in results
            ]
            document_ids = sorted({
                result["chunk"]["document_id"] for result in results
            })
            limits = []
            for document_id in document_ids:
                limits.extend(get_limits(document_id))
            search_ids = [result["chunk"]["chunk_id"] for result in results]
            limit_ids = list(dict.fromkeys(chunk["chunk_id"] for chunk in limits))
            final_ids = list(dict.fromkeys(search_ids + limit_ids))
            passed = evaluate_expected_ids(case, final_ids)
        except Exception as exc:
            errors += 1
            print(f"ERRO DE EXECUÇÃO — {type(exc).__name__}: {exc}")
            print("Contexto documental final: indisponível; expectativa não avaliada.")
            continue
        if passed:
            approved += 1
            print("APROVADO")
        else:
            failed += 1
            print("FALHOU")
        print("Busca:" if search_lines else "Busca: []")
        for line in search_lines:
            print(line)
        print("Limites acrescentados (por filtro, sem pontuação):" if limit_ids
              else "Limites acrescentados: []")
        for chunk_id in limit_ids:
            print(f"  {chunk_id}")
        print(f"Contexto documental final: {json.dumps(final_ids, ensure_ascii=False)}")
    return print_summary(approved, failed, errors, len(cases))


def main(cases_path=CASES_PATH):
    try:
        cases = load_cases(cases_path)
        search, get_limits = load_retrieval_functions()
    except Exception as exc:
        print(f"ERRO GLOBAL — {type(exc).__name__}: {exc}")
        print("Consultas não iniciadas; expectativas não avaliadas.")
        return 2
    return run_cases(cases, search, get_limits)


if __name__ == "__main__":
    raise SystemExit(main())
