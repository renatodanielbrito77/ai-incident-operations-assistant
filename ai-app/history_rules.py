def match_historical_incidents(
    historical_incidents: list[dict],
    log_entries: list[dict],
) -> list[dict]:
    """Compara textos completos de históricos já filtrados pela aplicação.

    Ignora caixa e espaços nas bordas, sem inferir relevância ou causa raiz.
    Mantém os textos originais e não modifica as entradas.
    """
    messages = {
        entry["message"].strip().casefold()
        for entry in log_entries
        if entry["message"].strip()
    }
    matches = []
    for incident in historical_incidents:
        matched_symptoms = []
        seen = set()
        for symptom in incident["symptoms"]:
            normalized = symptom.strip().casefold()
            if normalized in messages and normalized not in seen:
                matched_symptoms.append(symptom)
                seen.add(normalized)
        if matched_symptoms:
            matches.append({
                "historical_incident": incident,
                "matched_symptoms": matched_symptoms,
            })
    return matches
