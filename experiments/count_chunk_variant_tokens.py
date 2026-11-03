"""Conta tokens de três variantes sem carregar pesos ou gerar embeddings."""

import json
from pathlib import Path

from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer


MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNKS_PATH = Path(__file__).resolve().parent.parent / "data" / "chunks.json"


def build_variants(chunk):
    content = chunk["content"]
    headings = [f"Seção: {chunk['section']}"]
    if chunk.get("subsection"):
        headings.append(f"Subseção: {chunk['subsection']}")
    titles = [chunk["section"]]
    if chunk.get("subsection"):
        titles.append(chunk["subsection"])
    return (
        content,
        "\n".join(headings) + "\n\n" + content,
        " | ".join(titles) + "\n\n" + content,
    )


def main():
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    config_path = hf_hub_download(MODEL_ID, "sentence_bert_config.json")
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    sentence_limit = config["max_seq_length"]
    limit = min(sentence_limit, tokenizer.model_max_length)
    print(f"Modelo/tokenizer: {MODEL_ID}")
    print(f"Limite SentenceTransformer: {sentence_limit}")
    print(f"Limite do tokenizer: {tokenizer.model_max_length}")
    print(f"Limite usado para indicar excesso: {limit}")
    print("A: conteúdo; B: seção + subseção, quando presente + conteúdo")
    print('C: títulos presentes unidos por " | " + duas quebras de linha + conteúdo')
    print("Contagem inclui tokens especiais; truncamento desabilitado.")
    print("chunk_id | tokens A | tokens B | tokens C | excesso A | excesso B | excesso C")
    exceeded_a = exceeded_b = exceeded_c = 0
    for chunk in chunks:
        variant_a, variant_b, variant_c = build_variants(chunk)
        counts = [
            len(tokenizer(
                text, truncation=False, padding=False, add_special_tokens=True
            )["input_ids"])
            for text in (variant_a, variant_b, variant_c)
        ]
        over_a, over_b, over_c = (count > limit for count in counts)
        exceeded_a += over_a
        exceeded_b += over_b
        exceeded_c += over_c
        print(
            f"{chunk['chunk_id']} | {counts[0]} | {counts[1]} | {counts[2]} | "
            f"{'SIM' if over_a else 'não'} | {'SIM' if over_b else 'não'} | "
            f"{'SIM' if over_c else 'não'}"
        )
    print(f"Chunks acima do limite: A={exceeded_a}; B={exceeded_b}; C={exceeded_c}; total={len(chunks)}")


if __name__ == "__main__":
    main()
