from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI()


class HistoricalIncident(BaseModel):
    historical_incident_id: str
    application: str
    summary: str
    symptoms: list[str]
    resolution: str
    observed_result: str


class HistoricalIncidentsResponse(BaseModel):
    application: str
    historical_incidents: list[HistoricalIncident]


historical_incidents = [
    {
        "historical_incident_id": "HIST-001",
        "application": "checkout",
        "summary": "Timeouts nas chamadas ao serviço de pagamentos",
        "symptoms": [
            "Timeout while connecting to payment service",
            "Latência p95 acima de 1000 ms",
        ],
        "resolution": "A equipe reverteu uma alteração recente no pool de conexões do checkout.",
        "observed_result": "Os timeouts diminuíram durante os 30 minutos seguintes. Não foi comprovado que a configuração era a única causa.",
    },
    {
        "historical_incident_id": "HIST-002",
        "application": "checkout",
        "summary": "Erros de checkout durante indisponibilidade do provedor",
        "symptoms": [
            "Timeout while connecting to payment service",
            "Aumento da taxa de erros no checkout",
        ],
        "resolution": "A equipe acompanhou a recuperação realizada pelo provedor, sem alterar o checkout.",
        "observed_result": "A taxa de erros voltou ao nível habitual após a recuperação do provedor.",
    },
    {
        "historical_incident_id": "HIST-003",
        "application": "identity",
        "summary": "Falha no envio de mensagens de recuperação de senha",
        "symptoms": [
            "Password reset email delivery failed",
            "Usuários não recebiam mensagens de recuperação",
        ],
        "resolution": "A equipe atualizou a credencial expirada do serviço de envio de e-mails.",
        "observed_result": "Novas solicitações de recuperação tiveram entrega confirmada. Solicitações anteriores não foram reenviadas automaticamente.",
    },
]

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


@app.get("/historical-incidents", response_model=HistoricalIncidentsResponse)
def get_historical_incidents(application: str = Query(..., min_length=1)):
    return {
        "application": application,
        "historical_incidents": sorted(
            [
                incident for incident in historical_incidents
                if incident["application"] == application
            ],
            key=lambda incident: incident["historical_incident_id"],
        ),
    }


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
