"""Regras temporais puras: preservam textos, ordem e janela recebidos."""
from copy import deepcopy
from datetime import datetime
import re

_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise ValueError("Timestamp deve ser ISO 8601 com hora e fuso explícito")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timestamp sem fuso")
    return parsed


def validate_window(start: str, end: str) -> tuple[datetime, datetime]:
    a, b = parse_timestamp(start), parse_timestamp(end)
    if a > b:
        raise ValueError("Início da janela posterior ao fim")
    return a, b


def assess_temporal(incident: dict, monitoring: dict, log_entries: list[dict]) -> dict:
    start, end = validate_window(incident["window_start"], incident["window_end"])
    metric = parse_timestamp(monitoring["timestamp"])
    applicability, usable = [], []
    has_message = False
    for index, entry in enumerate(log_entries):
        timestamp = parse_timestamp(entry["timestamp"])
        filled = bool(entry["message"].strip())
        has_message = has_message or filled
        inside = start <= timestamp <= end
        applicability.append({
            "entry_index": index,
            "temporal_status": "within_window" if inside else "outside_window",
            "message_status": "filled" if filled else "blank",
        })
        if inside and filled:
            usable.append(deepcopy(entry))
    return {
        "assessment": {
            "window_start": incident["window_start"],
            "window_end": incident["window_end"],
            "monitoring_timestamp": monitoring["timestamp"],
            "monitoring_applicability": "within_window" if start <= metric <= end else "outside_window",
            "log_applicability": applicability,
            "log_status": "usable" if usable else ("LOGS_OUTSIDE_WINDOW" if has_message else "NO_LOG_MESSAGE"),
        },
        "applicable_log_entries": usable,
    }
