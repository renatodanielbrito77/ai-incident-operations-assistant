"""Valida uma candidata manual, sem rede, geração ou execução de ações."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ai-app"))

from pydantic import ValidationError
from recommendation_models import RecommendationCandidate, CandidateStructureReport
from recommendation_structure import check_candidate_structure
from recommendation_report import render_candidate_report


CHUNKS_PATH = ROOT / "data" / "chunks.json"
DOCUMENTATION_ID = "RB-001-04-02"
LIMIT_ID = "RB-001-05"


def load_example_context(path):
    chunks = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(chunks, list) or any(not isinstance(chunk, dict) for chunk in chunks):
        raise ValueError("A origem deve conter uma lista de chunks")
    selected = {}
    for chunk_id in (DOCUMENTATION_ID, LIMIT_ID):
        matches = [chunk for chunk in chunks if chunk.get("chunk_id") == chunk_id]
        if not matches:
            raise ValueError(f"Chunk obrigatório ausente na origem: {chunk_id}")
        if len(matches) != 1:
            raise ValueError(f"Chunk obrigatório duplicado na origem: {chunk_id}")
        selected[chunk_id] = matches[0]
    return [{"chunk": selected[DOCUMENTATION_ID]}], [selected[LIMIT_ID]]


def validation_details(exc):
    return [
        {"field": ".".join(str(part) for part in error["loc"]),
         "type": error["type"], "message": error["msg"]}
        for error in exc.errors()
    ]


def show_error(code, details, message="Avaliação estrutural não concluída; nenhum relatório emitido."):
    print(json.dumps({
        "error": code, "details": details,
        "message": message,
    }, ensure_ascii=False, indent=2))
    return 2


def run(candidate_path, chunks_path=CHUNKS_PATH, report_path=None):
    try:
        raw = Path(candidate_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return show_error("INPUT_ERROR", str(exc))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return show_error("JSON_INVALID", {
            "line": exc.lineno, "column": exc.colno, "message": exc.msg,
        })
    try:
        candidate = RecommendationCandidate.model_validate(data)
    except ValidationError as exc:
        return show_error("CONTRACT_INVALID", validation_details(exc))
    try:
        documentation, limits = load_example_context(chunks_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return show_error("CONTEXT_ERROR", str(exc))
    result = check_candidate_structure(candidate.model_dump(), documentation, limits)
    try:
        report = CandidateStructureReport.model_validate(result)
    except ValidationError as exc:
        return show_error("REPORT_CONTRACT_ERROR", validation_details(exc))
    if report_path is not None:
        markdown = render_candidate_report(candidate, report, documentation, limits)
        try:
            with Path(report_path).open("x", encoding="utf-8") as output:
                output.write(markdown)
        except (OSError, UnicodeError) as exc:
            return show_error(
                "REPORT_WRITE_ERROR", str(exc),
                "Avaliação estrutural concluída, mas a gravação do Markdown não foi confirmada. "
                "Um arquivo novo pode ter ficado incompleto; arquivos preexistentes não são sobrescritos.",
            )
    output_data = {
        "candidate": candidate.model_dump(),
        "context": {
            "documentation_chunk_ids": [DOCUMENTATION_ID],
            "document_limit_chunk_ids": [LIMIT_ID],
        },
        "report": report.model_dump(),
        "notice": "Verificações estruturais não comprovam suporte semântico nem autorizam execução. Nenhuma ação foi executada.",
    }
    if report_path is not None:
        output_data["markdown_report_path"] = str(report_path)
    print(json.dumps(output_data, ensure_ascii=False, indent=2))
    return 0 if report.structural_checks_passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument(
        "--report", type=Path,
        help="Caminho de um novo Markdown; o diretório deve existir e arquivos existentes não são sobrescritos.",
    )
    args = parser.parse_args()
    return run(args.candidate, report_path=args.report)


if __name__ == "__main__":
    raise SystemExit(main())
