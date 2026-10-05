# AI Incident Operations Assistant

POC local para construir e entender, incrementalmente, uma aplicação de apoio à investigação de incidentes.

## Estado atual

A aplicação recebe um identificador de incidente e consulta APIs com dados fictícios.

- **Não-P1:** consulta incidente, monitoring e logs e retorna um `InvestigationContext`.
- **P1:** retorna uma indicação de escalonamento manual e interrompe o fluxo antes de consultar monitoring e logs.

O escalonamento é apenas indicado na resposta. Nenhuma ação externa é executada.

## Estrutura

```text
ai-incident-operations-assistant/
├── ai-app/
│   └── main.py
├── mock-services/
│   └── main.py
└── README.md
```

Os serviços são executados diretamente no Mac, em dois terminais, usando o mesmo ambiente virtual `.venv`.

## Preparação do ambiente

Na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn httpx
```

Essa preparação é necessária apenas na primeira instalação. Para retomar o projeto, basta ativar o ambiente e iniciar os serviços.

## Iniciar Mock Services

Em um terminal, partindo da raiz do projeto:

```bash
source .venv/bin/activate
cd mock-services
python -m uvicorn main:app --reload --port 8001
```

Documentação interativa: [http://localhost:8001/docs](http://localhost:8001/docs)

Rotas:

- `GET /health`
- `GET /incidents/{incident_id}`
- `GET /monitoring/{application}`
- `GET /logs/{application}`

## Iniciar AI App

Em outro terminal, partindo da raiz do projeto:

```bash
source .venv/bin/activate
cd ai-app
python -m uvicorn main:app --reload --port 8000
```

Documentação interativa: [http://localhost:8000/docs](http://localhost:8000/docs)

Rotas:

- `GET /health`
- `POST /investigate/{incident_id}`

Mantenha os dois terminais em execução. Para parar um serviço, pressione `Ctrl+C` no terminal correspondente.

## Fluxo da investigação

```text
Receber incident_id
→ consultar incidente
→ verificar prioridade
    → P1: retornar indicação de escalonamento manual
    → não-P1:
        → consultar monitoring usando application
        → consultar logs usando application
        → retornar InvestigationContext
```

O FastAPI valida a resposta de sucesso conforme o `response_model` antes de enviá-la como JSON.

Os modelos declarados são:

- `Incident`
- `Monitoring`
- `LogEntry`
- `ApplicationLogs`
- `InvestigationContext`
- `EscalationResponse`

## Testes manuais

No `/docs` do AI App, abra `POST /investigate/{incident_id}`, clique em **Try it out**, informe o identificador e clique em **Execute**.

### INC-001 — prioridade P2

Resultado esperado: HTTP `200`, contendo:

```text
incident
monitoring
logs
```

### INC-002 — prioridade P1

Resultado esperado: HTTP `200`, contendo o incidente e:

```json
{
  "status": "manual_escalation_required",
  "reason": "Incidente P1 exige tratamento humano; investigação automática interrompida."
}
```

No terminal do Mock Services, deve aparecer somente a consulta ao incidente, sem consultas de monitoring ou logs para essa investigação.

### INC-999 — incidente inexistente

Resultado esperado: HTTP `404`.

```json
{
  "detail": "Incident not found"
}
```

### Mock Services desligado

Pare o Mock Services e investigue `INC-001` pelo AI App.

Resultado esperado: HTTP `503`, com uma mensagem de indisponibilidade.

Reinicie o Mock Services e repita a investigação. O resultado deve voltar a ser HTTP `200`.

## Tratamento de erros

| Código | Significado no código atual |
|---|---|
| `404` | Incidente, monitoring ou logs não encontrados |
| `503` | Falha de conexão com Mock Services (`httpx.ConnectError`) |
| `504` | Timeout na comunicação com Mock Services (`httpx.TimeoutException`) |

As três consultas usam `timeout=5.0`. Esse valor configura limites de espera nas operações de rede, não um limite único para toda a investigação.

O tratamento de timeout foi implementado, mas o cenário de HTTP `504` ainda não foi testado.

Outras falhas, como respostas HTTP inesperadas do Mock Services ou dados incompatíveis com os modelos, ainda podem resultar em HTTP `500`.

## Limitações e escopo

- Dados de incidentes, monitoring e logs são fictícios e mantidos em memória.
- A aplicação coleta contexto; ainda não analisa causas nem recomenda ações.
- P1 gera apenas uma indicação de escalonamento manual.
- Ainda não há LLM, RAG, Vector DB ou busca de incidentes históricos.
- Ainda não há Docker Compose, audit ou evals.
- Não há integração com AWS ou Kubernetes.

## Etapas futuras

A evolução será incremental: Docker Compose local, documentação fictícia, chunking, embeddings, Vector DB/RAG, incidentes históricos semelhantes, LLM, guardrails, audit e evals.

Posteriormente, será feita a comparação entre workflow determinístico e abordagem agentic.
