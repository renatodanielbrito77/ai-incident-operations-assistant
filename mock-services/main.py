from fastapi import FastAPI, HTTPException

app = FastAPI()

incidents = {
    "INC-001": {
        "incident_id": "INC-001",
        "application": "checkout",
        "priority": "P2",
        "summary": "Aumento de erros no checkout",
    },
    "INC-002": {
        "incident_id": "INC-002",
        "application": "checkout",
        "priority": "P1",
        "summary": "Checkout indisponível",
    },
    "INC-003": {
        "incident_id": "INC-003",
        "application": "identity",
        "priority": "P2",
        "summary": "Usuário não consegue recuperar a senha",
    },
}

monitoring = {
    "checkout": {
        "application": "checkout",
        "status": "degraded",
        "error_rate_percent": 12.5,
        "latency_p95_ms": 1800,
    },
    # No dicionário monitoring:
    "identity": {
        "application": "identity",
        "status": "degraded",
        "error_rate_percent": 8.0,
        "latency_p95_ms": 250.0,
    },
}

logs = {
    "checkout": {
        "application": "checkout",
        "entries": [
            {
                "timestamp": "2026-10-05T12:00:00Z",
                "level": "ERROR",
                "message": "Timeout while connecting to payment service",
            },
            {
                "timestamp": "2026-10-05T12:00:05Z",
                "level": "WARN",
                "message": "Payment request exceeded latency threshold",
            },
        ],
    },
    "identity": {
        "application": "identity",
        "entries": [
            {
                "timestamp": "2026-10-08T18:00:00Z",
                "level": "ERROR",
                "message": "Password reset email delivery failed",
            }
        ],
    },
}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    # Buscar o incidente no dicionário.
    # Se não existir, lançar HTTPException com status_code=404.
    # Se existir, retornar o incidente.
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents[incident_id]

@app.get("/monitoring/{application}")
def get_monitoring(application: str):
    # Buscar o status de monitoramento no dicionário.
    # Se não existir, lançar HTTPException com status_code=404.
    # Se existir, retornar o status de monitoramento.
    if application not in monitoring:
        raise HTTPException(status_code=404, detail="Application not found")
    return monitoring[application]

@app.get("/logs/{application}")
def get_logs(application: str):
    # Buscar os logs no dicionário.
    # Se não existir, lançar HTTPException com status_code=404.
    # Se existir, retornar os logs.
    if application not in logs:
        raise HTTPException(status_code=404, detail="Application not found")
    return logs[application]
