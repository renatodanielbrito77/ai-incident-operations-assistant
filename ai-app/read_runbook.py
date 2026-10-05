from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNBOOK_PATH = PROJECT_ROOT / "docs" / "runbooks" / "checkout-payment-timeout.md"

RUNBOOK_CONTENT = RUNBOOK_PATH.read_text(encoding="utf-8")

sections = RUNBOOK_CONTENT.split("\n## ")

chunks = []

for index, section in enumerate(sections[1:], start=1):
    section_title, _, section_body = section.partition("\n")

    chunk = {
        "chunk_id": f"RB-001-{index:02d}",
        "document_id": "RB-001",
        "source": RUNBOOK_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "section": section_title.strip(),
        "content": section_body.strip(),
    }

    chunks.append(chunk)

print(chunks[0])  # Exibe o primeiro chunk para verificação
print(f"Total de chunks: {len(chunks)}")  # Exibe o total de chunks gerados


OUTPUT_PATH = PROJECT_ROOT / "data" / "chunks.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")

print