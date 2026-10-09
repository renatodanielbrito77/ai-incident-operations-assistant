from search_qdrant import get_document_limits

limits = get_document_limits("RB-001")

for chunk in limits:
    print(f'{chunk["chunk_id"]} — {chunk["section"]}')
    print(chunk["content"])
    