import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNBOOK_PATH = PROJECT_ROOT / "data" / "chunks.json"

chunks = json.loads(RUNBOOK_PATH.read_text(encoding="utf-8"))

query = "demora na resposta"

matching_chunks = [
    chunk for chunk in chunks if query.lower() in chunk["content"].lower()
]

print(f"Total de chunks encontrados: {len(matching_chunks)}")
print(f"Exibindo os chunks encontrados:")

for chunk in matching_chunks:
    print(f'{chunk["chunk_id"]} — {chunk["section"]}')
