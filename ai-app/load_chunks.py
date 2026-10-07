import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "chunk_embeddings.json"

payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

chunks = payload["chunks"]
vectors = payload["embeddings"]

if len(chunks) != len(vectors):
    raise ValueError("A quantidade de chunks e vetores é diferente")

points = []

for chunk, vector in zip(chunks, vectors):
    points.append(PointStruct(
        id=str(uuid5(NAMESPACE_URL, chunk["chunk_id"])),
        vector=vector,
        payload=chunk,
    ))

client = QdrantClient(url="http://localhost:6333")

print(f"Registros preparados: {len(points)}")

result = client.upsert(
    collection_name="runbook_chunks",
    points=points,
    wait=True,
)

print(f"Upsert result: {result}")

