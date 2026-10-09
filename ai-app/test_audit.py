import json
from audit import build_audit_event
from pathlib import Path
from audit import append_audit_event

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDITH_PATH = PROJECT_ROOT / "data" / "audit" / "events.log"

event = build_audit_event(
    incident_id="INC-001",
    analysis_code="CONTEXT_READY",
    retrieved_chunk_ids=["RB-001-02-01", "RB-001-03-02", "RB-001-04-02"],
    limit_chunk_ids=["RB-001-05"],
)

print(json.dumps(event, ensure_ascii=False, indent=2))

append_audit_event(
    event, AUDITH_PATH
)
print(f"Evento salvo em {AUDITH_PATH}", flush=True)