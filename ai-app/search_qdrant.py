from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cpu"
)

client = QdrantClient(url="http://localhost:6333")

#query = "checkout lento ao consultar o serviço de pagamentos"
query = "como recuperar a senha de um usuário"

query_vector = model.encode(query).tolist()

response = client.query_points(
    collection_name="runbook_chunks",
    query=query_vector,
    limit=3,
    with_payload=True,
    score_threshold=0.50,
)

for point in response.points:
    score = point.score
    chunk = point.payload
    print(f"{score:.4f} — {chunk['chunk_id']}")