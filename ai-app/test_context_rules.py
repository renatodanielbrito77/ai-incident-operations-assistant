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

print("Os três cenários passaram.")