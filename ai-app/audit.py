from datetime import datetime, timezone
from uuid import uuid4
import json
from pathlib import Path
from typing import Literal


def build_audit_event(
    incident_id: str,
    analysis_code: str,
    retrieved_chunk_ids: list[str],
    limit_chunk_ids: list[str],
    stage: str = "unspecified",
    historical_incident_ids: list[str] | None = None,
    matched_historical_incident_ids: list[str] | None = None,
    historical_matching_status: Literal["not_evaluated", "evaluated"] = "not_evaluated",
):
    return {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_id": incident_id,
        "analysis_code": analysis_code,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "limit_chunk_ids": limit_chunk_ids,
        "stage": stage,
        "historical_incident_ids": (
            list(historical_incident_ids) if historical_incident_ids is not None else []
        ),
        "matched_historical_incident_ids": (
            list(matched_historical_incident_ids)
            if matched_historical_incident_ids is not None else []
        ),
        "historical_matching_status": historical_matching_status,
    }

def append_audit_event(event:dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(event, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
            
