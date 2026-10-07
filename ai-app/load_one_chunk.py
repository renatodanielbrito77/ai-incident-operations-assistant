import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "chunk_embeddings.json"

payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

chunk = payload["chunks"][0]
vector = payload["embeddings"][0]

client = QdrantClient(url="http://localhost:6333")

point = PointStruct(
    id=uuid5(NAMESPACE_URL, chunk["chunk_id"]),
    vector=vector,
    payload=chunk,
)

result = client.upsert(
    collection_name="runbook_chunks",
    points=[point],
    wait=True,
)

print(f"Upsert result: {result}")

