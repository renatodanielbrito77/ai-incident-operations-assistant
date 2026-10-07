import json
from pathlib import Path
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks.json"

chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device="cpu"
)

embedding = model.encode([chunk["content"] for chunk in chunks])

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

if __name__ == "__main__":
    print(f"Limite do modelo: {model.max_seq_length} tokens")

    for chunk in chunks:
        tokens = model.tokenizer(
            chunk["content"],
            truncation=False,
        )["input_ids"]

        print(f'{chunk["chunk_id"]}: {len(tokens)} tokens')

    results = search_chunks(
        "checkout lento ao consultar o serviço de pagamentos"
    )

    if not results:
        print("Nenhum trecho atingiu o limiar experimental.")
    else:
        for result in results:
            chunk = result["chunk"]
            print(f'{result["score"]:.4f} — {chunk["chunk_id"]}')

    print(f"Embedding shape: {embedding.shape}")

    OUTPUT_PATH = PROJECT_ROOT / "data" / "chunk_embeddings.json"

    payload = {
        "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "dimensions": int(embedding.shape[1]),
        "chunks": chunks,
        "embeddings": embedding.tolist(),
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Embeddings salvos em: {OUTPUT_PATH}")