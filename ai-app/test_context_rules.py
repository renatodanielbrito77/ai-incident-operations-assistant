from context_rules import evaluate_context

documentation = [
    {"chunk": {"document_id": "RB-001"}}
]

limits = [
    {"document_id": "RB-001"}
]

assert evaluate_context([], [])["analysis_status"] == "abstained"

missing_limits = evaluate_context(documentation, [])
assert missing_limits["analysis_status"] == "abstained"
assert "RB-001" in missing_limits["analysis_reason"]

assert (
    evaluate_context(documentation, limits)["analysis_status"]
    == "context_ready"
)

two_documents = [
    {"chunk": {"document_id": "RB-001"}},
    {"chunk": {"document_id": "RB-002"}},
]

partial_limits = [
    {"document_id": "RB-001"}
]

decision = evaluate_context(two_documents, partial_limits)

assert decision["analysis_status"] == "abstained"
assert decision["analysis_reason"] == (
    "Limites não encontrados para os documentos: RB-002"
)

print("Todos os cenários passaram.")