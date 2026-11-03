"""Experimento A/C isolado: cria coleções novas e nunca exclui coleções."""

import json
import os
from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid4, uuid5

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-app"))

from eval_common import evaluate_expected_ids
from eval_retrieval import load_cases
from count_chunk_variant_tokens import MODEL_ID, build_variants


PARENT = "RB-001-03-01"
PART_IDS = [f"{PARENT}-part-01", f"{PARENT}-part-02"]


def experimental_chunks(original):
    parent = next(chunk for chunk in original if chunk["chunk_id"] == PARENT)
    boundary = parent["content"].index("4. Comparar")
    contents = [parent["content"][:boundary], parent["content"][boundary:]]
    derived = [
        {**parent, "chunk_id": PART_IDS[index], "parent_chunk_id": PARENT,
         "part_index": index + 1, "content": content}
        for index, content in enumerate(contents)
    ]
    assert "".join(chunk["content"] for chunk in derived) == parent["content"]
    chunks = []
    for chunk in original:
        chunks.extend(derived if chunk["chunk_id"] == PARENT else [dict(chunk)])
    ids = [chunk["chunk_id"] for chunk in chunks]
    assert len(chunks) == 11 and len(set(ids)) == 11
    assert PARENT not in ids
    for chunk in derived:
        for key in ("document_id", "source", "section", "subsection"):
            assert chunk.get(key) == parent.get(key)
    return chunks


def covered_ids(ids):
    """O ID pai só é satisfeito quando os dois derivados foram recuperados."""
    covered = set(ids)
    if set(PART_IDS).issubset(covered):
        covered.add(PARENT)
    return covered


def show_parts(label, ids):
    parts = [part for part in PART_IDS if part in ids]
    detail = " — APENAS UM; não satisfaz o pai" if len(parts) == 1 else ""
    print(f"{label}: derivados {len(parts)}/2 {parts}{detail}", flush=True)


def document_limits(client, collection, document_id):
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    chunks = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            scroll_filter=Filter(must=[
                FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                FieldCondition(key="section", match=MatchValue(value="Limites")),
            ]),
            limit=100, offset=offset, with_payload=True, with_vectors=False,
        )
        chunks.extend(point.payload for point in points)
        if offset is None:
            return chunks


def main():
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

    original = json.loads((ROOT / "data/chunks.json").read_text(encoding="utf-8"))
    cases = load_cases(ROOT / "evals/retrieval_cases.json")
    assert len(cases) == 6
    chunks = experimental_chunks(original)
    model = SentenceTransformer(MODEL_ID, device="cpu")
    texts = {"A": [], "C": []}
    print(f"Modelo: {MODEL_ID}; limite: {model.max_seq_length}; top_k=3; limiar=0.50", flush=True)
    print("chunk_id | tokens A | tokens C", flush=True)
    for chunk in chunks:
        a, _, c = build_variants(chunk)
        counts = []
        for variant, text in (("A", a), ("C", c)):
            count = len(model.tokenizer(
                text, truncation=False, padding=False, add_special_tokens=True
            )["input_ids"])
            assert count <= model.max_seq_length, (chunk["chunk_id"], variant, count)
            texts[variant].append(text)
            counts.append(count)
        print(f"{chunk['chunk_id']} | {counts[0]} | {counts[1]}", flush=True)
    print("Reconstrução, origem, ordem, IDs únicos e limites de tokens: OK", flush=True)
    # Também impede truncamento silencioso das consultas neste experimento.
    for case in cases:
        assert len(model.tokenizer(case["query"], truncation=False)["input_ids"]) <= model.max_seq_length
    query_vectors = model.encode([case["query"] for case in cases]).tolist()
    client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
    before = {collection.name for collection in client.get_collections().collections}
    run_id = uuid4().hex
    collections = {variant: f"experiment_chunks_{run_id}_{variant.lower()}" for variant in texts}
    print("Coleções novas: " + json.dumps(collections), flush=True)
    assert not set(collections.values()) & before
    summaries = {}
    for variant, collection in collections.items():
        vectors = model.encode(texts[variant]).tolist()
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
        )
        client.upsert(collection_name=collection, wait=True, points=[
            PointStruct(id=str(uuid5(NAMESPACE_URL, chunk["chunk_id"])), vector=vector, payload=chunk)
            for chunk, vector in zip(chunks, vectors)
        ])
        counts = {"busca": {"approved": 0, "failed": 0, "errors": 0},
                  "contexto": {"approved": 0, "failed": 0, "errors": 0}}
        for case, query_vector in zip(cases, query_vectors):
            print(f"\n{variant} / {case['case_id']} — {case['query']}", flush=True)
            print(f"Esperados: {case['expected_chunk_ids']}", flush=True)
            try:
                points = client.query_points(
                    collection_name=collection, query=query_vector, limit=3,
                    score_threshold=0.50, with_payload=True,
                ).points
                search_ids = [point.payload["chunk_id"] for point in points]
                passed = evaluate_expected_ids(case, covered_ids(search_ids))
                counts["busca"]["approved" if passed else "failed"] += 1
                print("Busca vetorial: " + ("APROVADO" if passed else "FALHOU"), flush=True)
                for rank, point in enumerate(points, 1):
                    print(f"  {rank}. {point.payload['chunk_id']} score={point.score:.6f}", flush=True)
                if not points:
                    print("  []", flush=True)
                show_parts("Busca", search_ids)
            except Exception as exc:
                counts["busca"]["errors"] += 1
                counts["contexto"]["errors"] += 1
                print(f"ERRO DE BUSCA; contexto não avaliado: {type(exc).__name__}: {exc}", flush=True)
                continue
            try:
                limits = []
                for document_id in sorted({point.payload["document_id"] for point in points}):
                    limits.extend(document_limits(client, collection, document_id))
                limit_ids = list(dict.fromkeys(chunk["chunk_id"] for chunk in limits))
                final_ids = list(dict.fromkeys(search_ids + limit_ids))
                passed = evaluate_expected_ids(case, covered_ids(final_ids))
                counts["contexto"]["approved" if passed else "failed"] += 1
                print(f"Limites por filtro, sem pontuação: {limit_ids}", flush=True)
                print(f"Contexto documental final: {final_ids}", flush=True)
                show_parts("Contexto", final_ids)
                print("Resultado contexto: " + ("APROVADO" if passed else "FALHOU"), flush=True)
            except Exception as exc:
                counts["contexto"]["errors"] += 1
                print(f"ERRO DE CONTEXTO: {type(exc).__name__}: {exc}", flush=True)
        summaries[variant] = counts
    after = {collection.name for collection in client.get_collections().collections}
    assert before.issubset(after), "Coleção preexistente ausente ao final"
    print("\nRESUMOS: " + json.dumps(summaries), flush=True)
    print("Coleções experimentais preservadas; nenhuma coleção excluída.", flush=True)
    all_counts = [counts for variant in summaries.values() for counts in variant.values()]
    return 2 if any(c["errors"] for c in all_counts) else 1 if any(c["failed"] for c in all_counts) else 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        print(f"ERRO GLOBAL: {type(exc).__name__}: {exc}", flush=True)
        exit_code = 2
    raise SystemExit(exit_code)
