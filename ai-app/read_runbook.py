from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNBOOK_PATH = PROJECT_ROOT / "docs" / "runbooks" / "checkout-payment-timeout.md"

RUNBOOK_CONTENT = RUNBOOK_PATH.read_text(encoding="utf-8")

sections = RUNBOOK_CONTENT.split("\n## ")

chunks = []

for index, section in enumerate(sections[1:], start=1):
    section_title, _, section_body = section.partition("\n")
    section_title = section_title.strip()

    if section_title == "Orientações":
        parts = section_body.strip().split("### ")

        for part_index, part in enumerate(
            [part for part in parts if part.strip()],
            start=1,
        ):
            subsection_title, _, subsection_body = part.strip().partition("\n")

            chunks.append({
                "chunk_id": f"RB-001-{index:02d}-{part_index:02d}",
                "document_id": "RB-001",
                "source": RUNBOOK_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "section": section_title,
                "subsection": subsection_title.strip(),
                "content": subsection_body.strip(),
            })
    elif section_title == "Sintomas":
        signals, separator, caveat = section_body.strip().partition(
            "\n\nOs limiares"
        )

        if not separator:
            raise ValueError("Não foi encontrada a ressalva de Sintomas")

        parts = [
            ("Sinais observáveis", signals),
            ("Ressalva dos limiares", "Os limiares" + caveat),
        ]

        for part_index, (subsection_title, content) in enumerate(
            parts, start=1
        ):
            chunks.append({
                "chunk_id": f"RB-001-{index:02d}-{part_index:02d}",
                "document_id": "RB-001",
                "source": RUNBOOK_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "section": section_title,
                "subsection": subsection_title,
                "content": content.strip(),
            })
    elif section_title == "Verificações":
        checks, separator, caveat = section_body.strip().partition(
            "\n\nSe não houver"
        )

        if not separator:
            raise ValueError("Não foi encontrada a ressalva de Verificações")

        parts = [
            ("Lista de verificações", checks),
            ("Dados insuficientes", "Se não houver" + caveat),
        ]

        for part_index, (subsection_title, content) in enumerate(
            parts, start=1
        ):
            chunks.append({
                "chunk_id": f"RB-001-{index:02d}-{part_index:02d}",
                "document_id": "RB-001",
                "source": RUNBOOK_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "section": section_title,
                "subsection": subsection_title,
                "content": content.strip(),
            })
    else:
        chunks.append({
            "chunk_id": f"RB-001-{index:02d}",
            "document_id": "RB-001",
            "source": RUNBOOK_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "section": section_title,
            "content": section_body.strip(),
        })

print(chunks[0])  # Exibe o primeiro chunk para verificação
print(f"Total de chunks: {len(chunks)}")  # Exibe o total de chunks gerados


OUTPUT_PATH = PROJECT_ROOT / "data" / "chunks.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Chunks salvos em: {OUTPUT_PATH}") 