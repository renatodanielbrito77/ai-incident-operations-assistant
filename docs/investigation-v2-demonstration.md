# Demonstração técnica do fluxo V2 — 2026-11-06

## Escopo e resultado

Execução única dos quatro recortes sintéticos S1D2, usando a imagem existente, rede Compose, vetores controlados e somente a nova coleção `runbook_chunks_v2_checkout_flow_001`. Código da CLI e dos componentes não alterado nesta demonstração. Código de saída: **0**.

| Incidente | Estado observado | Pacote | Acessos documentais durante o caso |
| --- | --- | --- | --- |
| INC-V2-001 | CONTEXT_READY | Sim | 1 abertura do controle, 1 busca, 1 consulta de Limites, 1 montagem de pacote |
| INC-V2-002 | NO_LOG_MESSAGE | Não | 0 |
| INC-V2-003 | MONITORING_OUTSIDE_WINDOW | Não | 0 |
| INC-V2-004 | P1_MANUAL_ESCALATION | Não | 0 |

Instrumentação temporária envolveu os métodos de `DocumentControl` e `QdrantBackend`, sem substituir seu comportamento ou modificar módulos. Contou chamadas durante cada investigação e interromperia imediatamente a execução em erro/estado inesperado ou acesso documental nos casos 002–004. Leituras de inventário do Qdrant antes/depois são verificações externas aos casos e não estão incluídas nesses contadores. O wrapper foi preservado com os artefatos.

## Pré-verificação e preservação

Antes de criar estado/resultados, foram conferidos como livres: coleção, `working/document-control/runbook_chunks_v2_checkout_flow_001/` e `working/investigation-v2-results/demo-001/`. A verificação foi repetida imediatamente antes da CLI. Destinos já ocupados provocariam interrupção, sem exclusão ou recriação.

Após a execução:

- Nova coleção: oito pontos, estado `ready`.
- `RB-V2-001` 1.0 permanece `active`, revisão de classificação 1; `RB-V2-002` 0.7 permanece `unconfirmed`, revisão 1.
- As cinco coleções preexistentes mantiveram contagem e SHA-256 da representação canônica de IDs, payloads e vetores: `runbook_chunks` (10), as duas coleções experimentais A/C (11 cada) e as duas coleções V2 de validação anterior (8 cada).
- Os 48 arquivos de referência mantiveram seus hashes, incluindo `received/`, `working/materials/`, estado documental anterior e resultados da validação documental anterior. Nenhum arquivo foi acrescentado a `received/` ou `working/materials/`.
- Projeto montado somente leitura no container. Nenhum serviço reconstruído/reiniciado; nenhuma coleção anterior alterada.

Os hashes completos estão em `v2-flow-preflight.json` e `verification.json`, fora do Git. A conferência não significa garantia contra escritores externos concorrentes; é uma comparação antes/depois desta execução.

## Pacote de INC-V2-001

- Busca: `RB-V2-001@1.0:03`, `RB-V2-001@1.0:04`, `RB-V2-001@1.0:02`.
- Limites: `RB-V2-001@1.0:04`, seção `Limites`.
- Todos os documentos do contexto/pacote: `RB-V2-001`, versão `1.0`, status `active`. O procedimento não confirmado não entrou.
- Janela original: `2026-11-04T10:00:00Z` a `2026-11-04T10:10:00Z`.
- Logs: `10:02:00Z` e `10:04:00Z`, ambos preenchidos e dentro da janela. Monitoring: `10:05:00Z`, aplicável.
- `source_snapshot`, incidente, monitoring e logs do pacote foram comparados ao JSON de origem, preservando conteúdo, ordem, timestamps e metadados disponíveis. Nenhuma ampliação de janela.
- Identificador em resultado e pacote: **`v2-demo-no-persisted-audit-event`**. É marcador **sintético**, não evento persistido; não foi demonstrada correlação com audit real.

## Comandos executados

A partir da raiz do repositório, usando scripts de observação temporários. Estes comandos registram a execução já realizada; **não repetir com os mesmos destinos**, agora ocupados.

Pré-verificação, somente leitura dos materiais e do Qdrant:

```sh
docker run --rm --network ai-incident-operations-assistant_default \
  --mount type=bind,source=/private/tmp/v2-flow-preflight.py,target=/preflight.py,readonly \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data,target=/data,readonly \
  --env PYTHONDONTWRITEBYTECODE=1 \
  ai-incident-operations-assistant-ai-app python /preflight.py \
  > /private/tmp/v2-flow-preflight.json
```

Demonstração instrumentada, chamando `experiments/investigate_v2.py::main` existente:

```sh
docker run --rm --network ai-incident-operations-assistant_default \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/ai-incident-operations-assistant,target=/workspace,readonly \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data,target=/data \
  --mount type=bind,source=/private/tmp/v2-flow-preflight.py,target=/preflight.py,readonly \
  --mount type=bind,source=/private/tmp/v2-flow-preflight.json,target=/baseline.json,readonly \
  --mount type=bind,source=/private/tmp/v2-flow-demonstration.py,target=/demonstration.py,readonly \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  ai-incident-operations-assistant-ai-app python /demonstration.py \
  > /private/tmp/v2-flow-demonstration-output.txt
```

Argumentos efetivos da CLI, também preservados em `request.json`:

```text
--source-dir /data/working/materials --incident-id all
--qdrant-url http://vector-db:6333
--collection runbook_chunks_v2_checkout_flow_001
--state-dir /data/working/document-control/runbook_chunks_v2_checkout_flow_001
--output-dir /data/working/investigation-v2-results/demo-001
--controlled-vectors
```

## Artefatos e limitações

Raiz externa: `/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data/`.

- Estado persistente: `working/document-control/runbook_chunks_v2_checkout_flow_001/state.json` e `executor.lock`.
- Resultados: `working/investigation-v2-results/demo-001/`, com requisição, entradas com hash, resultados por caso, pacote no resultado de 001, resumo e `verification.json`.
- Proveniência preservada no mesmo diretório: `v2-flow-preflight.py`, `v2-flow-preflight.json`, `v2-flow-demonstration.py`, `v2-flow-demonstration-output.txt`. Artefatos externos não incluídos no Git.

Esta demonstração verifica **integração técnica**, não qualidade semântica, suficiência das orientações nem valor aos usuários. Não houve embeddings/LLM, geração de candidata, participantes, baseline, notificação ou gravação de audit. Os testes isolados anteriores continuam sendo evidência separada; esta execução não substitui seu alcance nem constitui nova revisão EGM. Lock e estado continuam dependendo do componente e caminho canônico; acesso direto ao Qdrant permanece fora desse controle. Esforço humano efetivo não medido. Sem commit ou push.
