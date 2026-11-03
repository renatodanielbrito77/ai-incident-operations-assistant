def has_log_message(log_entries: list[dict]) -> bool:
    """Indica presença de texto nos logs, sem avaliar relevância ou conteúdo."""
    return any(entry["message"].strip() for entry in log_entries)
