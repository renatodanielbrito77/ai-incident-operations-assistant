def evaluate_expected_ids(case, available_ids):
    available_ids = set(available_ids)
    if case["expected_behavior"] == "retrieve":
        return set(case["expected_chunk_ids"]).issubset(available_ids)
    return not available_ids


def print_summary(approved, failed, errors, total):
    print(f"\nAprovados: {approved}/{total}")
    print(f"Reprovados: {failed}")
    print(f"Erros de execução: {errors}")
    return 2 if errors else 1 if failed else 0
