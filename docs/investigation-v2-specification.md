# Investigação V2 — fluxo temporal e controle documental

## Recorte

Executor local separado, sobre o lote sintético S1D2 em `working/materials`.
Não modifica API, respostas HTTP, audit, dados ou coleção V1. Não gera recomendações.
`RB-V2-001` versão 1.0 permanece ativo; `RB-V2-002` versão 0.7 permanece não confirmado.
A demonstração usa vetores controlados e não mede qualidade de recuperação semântica.

## Contratos e ordem

1. `IncidentV2`: contrato existente acrescido de `window_start` e `window_end` obrigatórios. Datas ISO 8601 com segundos e fuso explícito; início não posterior ao fim.
2. P1 retorna `P1_MANUAL_ESCALATION`, antes de chamar provedores de evidência/histórico, encoder ou fábrica do controle documental. O analista aciona o responsável de plantão de Operações no canal corporativo existente. Endereço não informado; nenhuma notificação enviada.
3. Não-P1 valida `EvidenceSnapshotV2`: envelope fictício, incidente, monitoring com timestamp, logs e fontes adicionais fornecidas. Aplicações e incidente devem corresponder. Timestamp inválido/sem fuso é erro de contrato, inclusive com logs vazios.
4. Comparações temporais usam instantes e extremos inclusivos. Valores textuais, fusos, ordem, metadados adicionais e tipos numéricos das evidências permanecem preservados. Não se amplia a janela.
5. Nenhuma mensagem preenchida após `strip()` → `NO_LOG_MESSAGE`. Mensagens preenchidas somente fora da janela → `LOGS_OUTSIDE_WINDOW`. Ambos solicitam logs da janela original, sem histórico ou busca documental.
6. Monitoring fora da janela → `MONITORING_OUTSIDE_WINDOW`: mantém as métricas, identifica que não se aplicam ao período e solicita as corretas antes da busca/histórico.
7. Com evidências aplicáveis, recupera históricos da aplicação, preservando sua incompletude e metadados. Apenas mensagens preenchidas dentro da janela participam da comparação histórica e da consulta documental. Todos os logs permanecem no contexto; `temporal_assessment.log_applicability` identifica cada posição e `applicable_log_entries` contém o subconjunto usado.
8. Abre o controle documental existente, sob lock e estado canônico persistente. Reutiliza filtro de ativos antes do top 3, limiar 0,50, auditoria dos payloads e Limites da mesma versão. Status não é inferido por idade/conteúdo.
9. Reutiliza `evaluate_context`. Sem documentação elegível → `NO_DOCUMENTATION`; sem Limites → `MISSING_DOCUMENT_LIMITS`. Inconsistência documental não vira lista vazia.
10. Somente `CONTEXT_READY` produz `InvestigationPackageV2`. Reutiliza instruções oficiais e schema de candidata da montagem anterior; valida e preserva evidências V2, metadados documentais e `audit_event_id`. Nenhuma chamada ao LLM.

A montagem de pacote compartilha uma projeção do contrato anterior, sem duplicar suas instruções. O caminho temporal é selecionado explicitamente por `investigation_schema_version="2.0"`. O contrato anterior continua disponível. No pacote, `schema_version="1.0"` e `document_policy_version="1.0"` são herdados; `investigation_schema_version="2.0"` identifica a extensão temporal.

## Saídas

`InvestigationResultV2` inclui estado, etapa, identificador recebido, evidências/avaliação temporal disponíveis, históricos recuperados, correspondências, solicitações, encaminhamento, contexto/pacote ou erro. `candidate_produced` é sempre falso.

| Estado | Pacote | Significado |
| --- | --- | --- |
| `P1_MANUAL_ESCALATION` | Não | Encaminhamento humano, sem dependência documental |
| `NO_LOG_MESSAGE` / `LOGS_OUTSIDE_WINDOW` | Não | Solicitação de mensagem/logs aplicáveis |
| `MONITORING_OUTSIDE_WINDOW` | Não | Solicitação de métricas do período correto |
| `NO_DOCUMENTATION` / `MISSING_DOCUMENT_LIMITS` | Não | Encerramento documental controlado |
| `CONTEXT_READY` | Sim | Contexto validado, sem geração |
| `CONTRACT_ERROR` | Não | Entrada inválida |
| `DOCUMENT_INTEGRITY_ERROR` | Não | Divergência documental, distinta de ausência |
| `DOCUMENT_CONTROL_ERROR` | Não | Bloqueio/estado/controle indisponível |
| `OPERATIONAL_ERROR` | Não | Outra falha de execução, sem ocultação como ausência |

A CLI retorna 0 nos encerramentos legítimos, inclusive solicitação/abstenção/P1, e 2 quando existe erro. O consumidor deve conferir `state` e `package_produced`.
O identificador da função é recebido, não criado. A CLI usa o marcador explícito `v2-demo-no-persisted-audit-event`: ele **não representa um evento persistido**, nem demonstra correlação real de audit.

## Arquivos e limites

Novos: `temporal_rules.py`, `investigation_v2_models.py`, `investigation_v2.py`, quatro arquivos de teste e `experiments/investigate_v2.py`. Alteração existente: somente extensão explícita em `document_collection.py::package`. Esta especificação e o card registram a entrega.

O controle continua local: lock e estado protegem operações realizadas pelo componente e pelo mesmo caminho canônico; acesso direto ao Qdrant pode contorná-los. Não há novas garantias distribuídas ou integração à API. A aplicabilidade temporal não prova suficiência semântica nem causa raiz. Históricos não autorizam repetir intervenções. A CLI arquiva o envelope lido antes da decisão P1, mas o fluxo não valida/coleta evidências nem abre controle nesse caminho.

## Testes isolados

Executados na imagem existente, projeto somente leitura, rede desativada, estado temporário em `/var/tmp` do container, sem volumes de audit. Sem descoberta geral:

```sh
docker run --rm --network none \
  --mount type=bind,source="$PWD",target=/workspace,readonly \
  --workdir /workspace/ai-app \
  --env PYTHONDONTWRITEBYTECODE=1 --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
  ai-incident-operations-assistant-ai-app \
  python -m unittest -v \
  test_temporal_rules test_investigation_v2_models test_investigation_v2 test_investigate_v2_cli \
  test_document_policy test_document_collection test_document_control_cli \
  test_llm_input_package test_document_limits_failure
```

Resultado final: **88 testes aprovados**, código **0** (33 novos e 55 de regressão). As mensagens de erro impressas pelos cenários negativos são esperadas; o resultado da suíte é `OK`.

Cobertura: fusos equivalentes/extremos, logs mistos/antigos/vazios, métricas antigas, contratos inválidos, P1 sem acesso downstream, preservação/serialização, dados temporais adulterados, filtro antes do ranking, versão dos Limites, reclassificação, bloqueio persistente, recuperação e exclusividade do controle anterior. Vetores e backend simulados; não é validação real nem avaliação semântica.

## Comando da demonstração real

Demonstração autorizada e concluída: [resultados e comandos efetivamente executados](investigation-v2-demonstration.md). Os destinos abaixo estão agora ocupados; **não repetir** sem novo planejamento autorizado. Uma coleção nova: `runbook_chunks_v2_checkout_flow_001` (oito chunks do lote aprovado, vetores controlados de duas dimensões). Coleção já existente é recusada pelo carregamento. Estado/destino de resultados existentes também são recusados; não substituir arquivos para repetir a demonstração.

Comando a partir da raiz do projeto, usando imagem existente e rede Compose:

```sh
docker run --rm --network ai-incident-operations-assistant_default \
  --mount type=bind,source="$PWD",target=/workspace,readonly \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data,target=/data \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  ai-incident-operations-assistant-ai-app \
  python /workspace/experiments/investigate_v2.py \
  --source-dir /data/working/materials --incident-id all \
  --qdrant-url http://vector-db:6333 \
  --collection runbook_chunks_v2_checkout_flow_001 \
  --state-dir /data/working/document-control/runbook_chunks_v2_checkout_flow_001 \
  --output-dir /data/working/investigation-v2-results/demo-001 \
  --controlled-vectors
```

Escritas externas ao Git:

- `working/document-control/runbook_chunks_v2_checkout_flow_001/`: `state.json`, `executor.lock` e arquivos temporários de substituição atômica do estado.
- `working/investigation-v2-results/demo-001/`: `request.json`, entrada com hash e resultado/erro por caso, `summary.json`; pacote dentro do resultado de 001.
- Qdrant: somente a nova coleção acima. Preservar `runbook_chunks`, coleções experimentais e as duas coleções da validação documental anterior.

O lote original, seus hashes e classificações não são alterados. Se uma carga falhar parcialmente, o bloqueio persistente existente continua aplicável; esta CLI não reconcilia nem repete automaticamente.
