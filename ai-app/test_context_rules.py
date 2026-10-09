from context_rules import evaluate_context

documentation = [
    {"chunk": {"document_id": "RB-001"}}
]

limits = [
    {"document_id": "RB-001"}
]

# 1. Sem documentação
no_documentation = evaluate_context([], [])

assert no_documentation["analysis_status"] == "abstained"
assert no_documentation["analysis_code"] == "NO_DOCUMENTATION"

# 2. Documento sem Limites
missing_limits = evaluate_context(documentation, [])

assert missing_limits["analysis_status"] == "abstained"
assert missing_limits["analysis_code"] == "MISSING_DOCUMENT_LIMITS"
assert "RB-001" in missing_limits["analysis_reason"]

# 3. Documentação e Limites presentes
ready = evaluate_context(documentation, limits)

assert ready["analysis_status"] == "context_ready"
assert ready["analysis_code"] == "CONTEXT_READY"

# 4. Dois documentos, mas Limites para apenas um
two_documents = [
    {"chunk": {"document_id": "RB-001"}},
    {"chunk": {"document_id": "RB-002"}},
]

partial_limits = [
    {"document_id": "RB-001"}
]

decision = evaluate_context(two_documents, partial_limits)

assert decision["analysis_status"] == "abstained"
assert decision["analysis_code"] == "MISSING_DOCUMENT_LIMITS"
assert decision["analysis_reason"] == (
    "Limites não encontrados para os documentos: RB-002"
)

print("Os quatro cenários passaram.")