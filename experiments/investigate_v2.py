"""Demonstração V2 isolada. Não chama API/LLM/audit nem toca a coleção V1."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai-app"))
from document_collection import ControlError, DocumentControl, QdrantBackend
from investigation_v2 import investigate_v2

COLLECTION = "runbook_chunks_v2_checkout_flow_001"
AUDIT_MARKER = "v2-demo-no-persisted-audit-event"
CASES = ("INC-V2-001", "INC-V2-002", "INC-V2-003", "INC-V2-004")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--incident-id", choices=(*CASES, "all"), default="all")
    parser.add_argument("--collection", default=COLLECTION)
    parser.add_argument("--qdrant-url", default="http://vector-db:6333")
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--controlled-vectors", action="store_true", required=True,
                        help="Obrigatório: ensaio de fluxo, não recuperação semântica")
    args = parser.parse_args(argv)
    out, source = Path(args.output_dir), Path(args.source_dir)
    try:
        out.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        print(f"ERRO: destino existente/indisponível: {exc}")
        return 2

    def write(name, value):
        with (out / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)

    write("request.json", {**vars(args), "audit_event_id": AUDIT_MARKER,
                           "audit_note": "Marcador sintético; nenhum evento de audit persistido"})
    loaded = False

    @contextmanager
    def documents():
        nonlocal loaded
        # Esta função só é invocada depois de P1 e dos gates temporais.
        if not loaded and Path(args.state_dir).exists():
            raise ControlError("Estado de demonstração já existe; não reutilizar/sobrescrever")
        with DocumentControl(args.state_dir, args.collection, args.qdrant_url,
                             QdrantBackend(args.qdrant_url, args.collection)) as control:
            if not loaded:
                from document_control import prepare
                chunks = prepare(source)  # Confere manifesto aprovado sem gerar embeddings.
                vectors = [[0.8, 0.6] if c["document_status"] == "active" else [1.0, 0.0] for c in chunks]
                control.load(chunks, vectors, 2)
                loaded = True
            yield control

    def histories(application):
        directory = source / "history"
        if not directory.is_dir():
            raise FileNotFoundError("Diretório de históricos não fornecido")
        values = [json.loads(p.read_text()) for p in sorted(directory.glob("*.json"))]
        return [v for v in values if v.get("application") == application]

    summary = []
    for case in CASES if args.incident_id == "all" else (args.incident_id,):
        try:
            path = source / "incidents" / f"{case}.json"
            original = path.read_bytes()
            raw = json.loads(original)
            # Arquiva o envelope sem interpretar evidências; o fluxo P1 não as valida/coleta.
            write(f"{case}-input.json", {"snapshot": raw, "sha256": hashlib.sha256(original).hexdigest()})
            result = investigate_v2(raw["incident"], evidence_provider=lambda: raw,
                                    history_provider=histories, document_control_factory=documents,
                                    encode_query=lambda query: [1.0, 0.0], audit_event_id=AUDIT_MARKER)
            write(f"{case}-result.json", result.model_dump(mode="json"))
            summary.append(dict(incident_id=case, state=result.state, stage=result.stage,
                                candidate_produced=False, package_produced=result.package is not None))
            print(f"{case}: {result.state}; package={result.package is not None}")
        except Exception as exc:
            write(f"{case}-error.json", dict(error_type=type(exc).__name__, message=str(exc)))
            summary.append(dict(incident_id=case, state="OPERATIONAL_ERROR", candidate_produced=False,
                                package_produced=False))
    write("summary.json", dict(controlled_vectors=True, semantic_evaluation=False, cases=summary))
    return 2 if any(c["state"].endswith("ERROR") for c in summary) else 0


if __name__ == "__main__":
    raise SystemExit(main())
