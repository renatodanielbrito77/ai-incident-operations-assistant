# AI Incident Operations Assistant

POC local para aprender e construir, incrementalmente, uma aplicação de apoio à
investigação de incidentes. O fluxo é determinístico: reúne evidências atuais,
históricos e documentação, verifica limites e registra o resultado em audit.

Consulte a [arquitetura e o mapa dos módulos](docs/architecture.md) para os
contratos, diagramas e detalhes do tratamento de falhas.

## Funcionalidades atuais

- Consulta incidente, históricos da mesma aplicação, monitoring e logs fictícios.
- Interrompe incidentes P1 antes de consultar históricos, monitoring ou logs,
  retornando uma indicação de escalonamento humano.
- Solicita dados adicionais quando não recebe nenhuma mensagem de log preenchida.
- Compara sintomas históricos com mensagens atuais por igualdade de texto completo,
  ignorando caixa e espaços nas bordas; não atribui pontuação semântica.
- Recupera trechos do runbook no Qdrant e acrescenta a seção `Limites` dos documentos
  recuperados, por filtro.
- Decide entre contexto pronto e abstenção por ausência de documentação ou limites.
- Persiste eventos JSONL e retorna `audit_event_id` para correlacionar respostas
  de negócio ao evento correspondente.
- Possui testes isolados, avaliações de busca e de contexto documental final, além
  de experimentos separados de representação dos chunks.

Não há LLM ou geração automática de recomendações. Históricos são experiências
passadas, não autorização para repetir uma resolução. Nenhuma ação corretiva ou
notificação de escalonamento é executada.

## Estrutura

```text
.
├── compose.yaml
├── ai-app/                  # API, regras, recuperação, audit, testes e avaliadores
├── mock-services/           # APIs fictícias e testes de históricos
├── data/                    # Chunks e embeddings preparados em arquivo
├── docs/
│   ├── architecture.md
│   └── runbooks/            # Documentação fictícia de investigação
├── evals/
│   └── retrieval_cases.json # Seis expectativas de recuperação
└── experiments/             # Scripts e relatório; não substituem o índice oficial
```

## Executar com Docker Compose

Pré-requisitos: Docker com Compose e acesso aos recursos necessários para construir
as imagens e obter os pesos do modelo. Na raiz do projeto:

```bash
docker compose up -d --build
```

| Serviço | Acesso pelo host | Persistência |
|---|---|---|
| AI App | [API interativa](http://localhost:8000/docs), porta 8000 | `audit-data` em `/app/audit` |
| Mock Services | [API interativa](http://localhost:8001/docs), porta 8001 | Dados em memória |
| Qdrant (`vector-db`) | `http://localhost:6333` | `qdrant-data` em `/qdrant/storage` |

As portas do Compose estão vinculadas a `127.0.0.1`. Dentro da rede, a AI App usa
`http://mock-services:8000` e `http://vector-db:6333`.

A inicialização da AI App importa o modelo
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, em CPU, e pode
baixar os pesos. Aguarde a conclusão antes de consultar `/health`. O Compose
expressa dependências, mas não configura verificações de prontidão dos serviços.

Após mudar somente o código da AI App, para reconstruí-la e recriá-la sem reiniciar
as dependências:

```bash
docker compose up -d --no-deps --build ai-app
```

O build copia os módulos para a imagem. Editar arquivos locais não atualiza
automaticamente o serviço em execução. Os scripts de testes, avaliadores e dados
não são copiados pelo Dockerfile; os comandos adiante usam montagem do projeto.

### Preparar a base documental

Subir os serviços **não cria nem popula automaticamente** `runbook_chunks`.
Os scripts abaixo são de preparação, não testes isolados: criam a coleção se
necessário, regeneram arquivos em `data/` e fazem upsert no Qdrant. Execute-os
somente quando quiser preparar ou atualizar essa base, com Qdrant disponível.

Na raiz do projeto, usando a imagem já construída:

```bash
# Coleção de 384 dimensões e distância cosseno; cria somente se ausente.
docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace:ro" -w /workspace ai-app \
  python -B /workspace/ai-app/test_qdrant.py

# Montagem gravável para gerar data/chunks.json.
docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace" -w /workspace ai-app \
  python -B /workspace/ai-app/read_runbook.py

# Gera data/chunk_embeddings.json; carrega o modelo.
docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace" -w /workspace ai-app \
  python -B /workspace/ai-app/embed_chunks.py

# Grava os vetores e payloads na coleção runbook_chunks.
docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace:ro" -w /workspace ai-app \
  python -B /workspace/ai-app/load_chunks.py
```

Os scripts não removem pontos antigos que deixaram de existir nos arquivos.
Uma revisão do índice deve considerar isso separadamente.

### Configuração e execução fora do Compose

| Variável | Padrão no código | Valor no Compose |
|---|---|---|
| `MOCK_SERVICES_URL` | `http://localhost:8001` | `http://mock-services:8000` |
| `QDRANT_URL` | `http://localhost:6333` | `http://vector-db:6333` |
| `AUDIT_PATH` | `/app/audit/events.jsonl` | `/app/audit/events.jsonl` |

Para uma execução local alternativa, instale as dependências de
[ai-app/requirements.txt](ai-app/requirements.txt) e
[mock-services/requirements.txt](mock-services/requirements.txt) no ambiente
escolhido. A AI App também precisa do Qdrant e da base preparada. Configure um
`AUDIT_PATH` gravável no host; `/app/audit` é o caminho padrão do container.

## API e fluxo de investigação

AI App: `GET /health` e `POST /investigate/{incident_id}`.

Mock Services: `GET /health`, `GET /incidents/{incident_id}`,
`GET /historical-incidents?application=...`, `GET /monitoring/{application}` e
`GET /logs/{application}`. A consulta de históricos usa igualdade exata de
aplicação, ordena por ID e retorna HTTP 200 com lista vazia quando não há registros.

```text
Consultar incidente
→ verificar prioridade
  → P1: persistir audit e retornar escalonamento manual
  → não-P1: consultar históricos → monitoring → logs
    → sem mensagem preenchida: persistir audit e solicitar dados adicionais
    → com mensagem: comparar históricos com logs
      → buscar documentação → recuperar Limites → avaliar contexto
      → persistir audit e retornar InvestigationContext
```

A verificação de logs usa apenas `message.strip()`: não interpreta resumo,
severidade ou significado da mensagem. A comparação histórica retorna
`historical_incident_matches`, com `historical_incident` e `matched_symptoms`,
preservando todos os registros em `historical_incidents`. Histórico não substitui
mensagens atuais, documentação ou limites.

As três respostas de negócio são validadas por modelos Pydantic:

| Modelo | Resultado HTTP 200 |
|---|---|
| `InvestigationContext` | Evidências, históricos, correspondências, documentação, limites e decisão |
| `EscalationResponse` | `status="manual_escalation_required"` |
| `MissingLogMessageResponse` | `status="additional_data_required"`, `analysis_code="NO_LOG_MESSAGE"`, motivo e `requested_data` |

No contexto de investigação, `analysis_status` é `context_ready` ou `abstained`.
Os códigos são `CONTEXT_READY`, `NO_DOCUMENTATION` e `MISSING_DOCUMENT_LIMITS`.
HTTP 200 não significa que a investigação identificou uma causa ou que há dados
suficientes para uma recomendação.

### Cenários fornecidos

Com a base oficial preparada, os cenários de referência são:

| Incidente/cenário | HTTP | Resultado |
|---|---|---|
| INC-001, checkout P2 | 200 | `CONTEXT_READY`, dois históricos e duas correspondências com o timeout |
| INC-003, identity P2 | 200 | `NO_DOCUMENTATION`, abstenção, um histórico e uma correspondência com a falha de envio de e-mail |
| INC-002, checkout P1 | 200 | Escalonamento manual; somente o incidente é consultado |
| INC-999 | 404 | `{"detail":"Incident not found"}` |
| Logs vazios ou todas as mensagens em branco | 200 | `NO_LOG_MESSAGE`; não compara históricos nem consulta documentação |

O Mock atual contém mensagens nos incidentes existentes; não há um incidente
adicional dedicado a logs vazios. Esse cenário é coberto por testes isolados.
Os resultados documentais dependem do índice e do modelo; não são valores
codificados por incidente na AI App.

## Audit e falhas

Cada evento contém UUID `event_id`, timestamp UTC, incidente, `analysis_code`,
`stage`, IDs de chunks e limites, além de:

- `historical_incident_ids`: todos os históricos recuperados.
- `matched_historical_incident_ids`: históricos com correspondência textual.
- `historical_matching_status`: `not_evaluated` ou `evaluated`; lista vazia com
  `evaluated` indica comparação concluída sem correspondências.

As três respostas de negócio incluem `audit_event_id`, reutilizando o ID do evento
após a persistência. Respostas de erro não expõem esse campo. Falha de gravação
interrompe o retorno com HTTP 503. O armazenamento é JSONL em volume; não há
`fsync`, API de consulta do audit ou garantia de durabilidade contra queda abrupta.

| HTTP | Tratamento implementado |
|---|---|
| 404 | Incidente, monitoring ou logs não encontrados |
| 503 | `httpx.ConnectError` no Mock, `ResponseHandlingException` na base documental ou `OSError` na gravação de audit |
| 504 | `httpx.TimeoutException` na comunicação com Mock Services |

O cliente HTTP é reutilizado e configurado com `timeout=5.0`; isso não é um limite
único de duração da investigação. Conexão e timeout possuem testes isolados por
etapa. Outras falhas HTTP, payloads inválidos ou exceções não tratadas podem resultar
em HTTP 500. Monitoring e logs com 404 não possuem evento próprio no fluxo atual.

## Testes isolados

Com a imagem existente, execute explicitamente os módulos abaixo no container
sem rede e sem montar volumes de dados. A partir da raiz do projeto:

```bash
docker run --rm --network none \
  --mount "type=bind,source=$PWD,target=/workspace,readonly" \
  --workdir /workspace/ai-app ai-incident-operations-assistant-ai-app \
  python -B -m unittest -v \
  test_evidence_rules test_history_rules test_audit_historical_ids \
  test_audit_event_id test_document_limits_failure \
  test_eval_retrieval test_eval_document_context
```

O nome da imagem acima corresponde ao nome padrão deste projeto no Compose;
confira `docker compose images` se usar outro nome de projeto. Os testes de API
substituem `search_qdrant` antes da importação, evitando carregar embeddings.
A persistência é simulada ou usa JSONL em diretório temporário, sem o volume real.

Para os testes isolados do Mock, use a mesma imagem, que já contém HTTPX:

```bash
docker run --rm --network none \
  --mount "type=bind,source=$PWD,target=/workspace,readonly" \
  --workdir /workspace/mock-services ai-incident-operations-assistant-ai-app \
  python -B -m unittest -v test_historical_incidents
```

`test_context_rules.py` é um script de asserções puras que pode ser executado
explicitamente. Evite descoberta geral: outros arquivos `test_*.py` são scripts
manuais que acessam serviços, carregam modelos ou gravam dados, como
`test_qdrant.py`, `test_search.py`, `test_limits.py`, `test_embedding.py` e
`test_audit.py`.

## Avaliações reais de recuperação

Os seis casos em [evals/retrieval_cases.json](evals/retrieval_cases.json) expressam
comportamentos desejados. Reprovações não devem ser corrigidas mudando as
expectativas para reproduzir a saída atual.

| Executor | O que avalia |
|---|---|
| `eval_retrieval.py` | IDs retornados pela busca vetorial |
| `eval_document_context.py` | União dos IDs da busca com os Limites dos documentos recuperados |

Ambos usam `top_k=3` e `min_similarity=0.50`. Para `retrieve`, todos os IDs esperados
devem estar presentes; para `abstain`, o resultado avaliado deve estar vazio.
Limites obtidos por filtro não recebem pontuação. Erros nunca viram lista vazia.
Códigos de saída: `0` para aprovação integral, `1` para reprovação de expectativa,
`2` para erro global ou operacional; erro tem precedência sobre reprovação.

Execute cada avaliador separadamente, com a imagem existente e Qdrant disponível:

```bash
docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace:ro" -w /workspace ai-app \
  python -B /workspace/ai-app/eval_retrieval.py

docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace:ro" -w /workspace ai-app \
  python -B /workspace/ai-app/eval_document_context.py
```

Esses executores usam a rede e carregam o modelo, mas não importam a API nem gravam
audit. Não são os testes unitários com funções simuladas descritos acima.

## Experimentos e limites da POC

A comparação de conteúdo versus títulos e conteúdo está registrada no
[relatório experimental](experiments/chunk_embedding_comparison_report.md).
A decisão registrada é manter o índice oficial `runbook_chunks`. Os scripts de
`experiments/` são separados do fluxo da API; a comparação gera embeddings e cria
coleções próprias com nomes únicos, sem excluir as preexistentes. A contagem de
tokens não gera embeddings.

A POC usa dados fictícios, um runbook e apenas seis casos de avaliação. O filtro de
históricos é por aplicação, sem busca semântica. Texto de log preenchido não
comprova relevância ou causa raiz; não há correlação temporal validada. Não há
LLM, geração de respostas, ações corretivas automáticas ou integração com AWS e
Kubernetes. Uma evolução futura deve ser avaliada separadamente e manter esses
limites explícitos.
