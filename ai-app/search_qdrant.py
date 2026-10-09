from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import os
from qdrant_client.models import Filter, FieldCondition, MatchValue

model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cpu"
)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

client = QdrantClient(url=QDRANT_URL)

query = "checkout lento ao consultar o serviço de pagamentos"

def search_chunks(query: str, top_k: int = 3, min_similarity: float = 0.50):
    query_vector = model.encode(query).tolist()

    response = client.query_points(
        collection_name="runbook_chunks",
        query=query_vector,
        limit=top_k,
        with_payload=True,
        score_threshold=min_similarity,
    )

    return [
        {
            "score": point.score,
            "chunk": point.payload,
        }
        for point in response.points
    ]

def get_document_limits(document_id: str):
    chunks = []
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name="runbook_chunks",
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    ),
                    FieldCondition(
                        key="section",
                        match=MatchValue(value="Limites"),
                    ),
                ]
            ),
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        chunks.extend(point.payload for point in points)

        if offset is None:
            break

    return chunks

if __name__ == "__main__":
    results = search_chunks(
        "checkout lento ao consultar o serviço de pagamentos"
    )

    if not results:
        print("Nenhum trecho atingiu o limiar experimental.")
    else:
        for result in results:
            print(
                f'{result["score"]:.4f} — '
                f'{result["chunk"]["chunk_id"]}'
            )