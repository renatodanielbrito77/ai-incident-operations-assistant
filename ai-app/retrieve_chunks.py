import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "chunk_embeddings.json"

payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

chunks = payload["chunks"]
embedding = np.array(payload["embeddings"], dtype=np.float32)

if embedding.ndim != 2:
    raise ValueError("Os embeddings devem formar uma matriz")

if len(chunks) != embedding.shape[0]:
    raise ValueError("A quantidade de chunks e vetores é diferente")

if embedding.shape[1] != payload["dimensions"]:
    raise ValueError("A dimensão dos vetores difere da registrada no arquivo")

model = SentenceTransformer(payload["model"], device="cpu")

def search_chunks(query: str, top_k: int = 3, min_similarity: float = 0.50):
    query_embedding = model.encode(query)
    scores = model.similarity(query_embedding, embedding)[0]

    ranked_indices = sorted(
        range(len(chunks)),
        key=lambda index: float(scores[index]),
        reverse=True,
    )

    selected_indices = [
        index
        for index in ranked_indices
        if float(scores[index]) >= min_similarity
    ][:top_k]

    return [
        {
            "score": float(scores[index]),
            "chunk": chunks[index],
        }
        for index in selected_indices
    ]
