# Controle documental V2 — validação funcional real

Data: 2026-11-06. Execução autorizada após a revisão EGM. **Resultado funcional:
aprovado nos cenários abaixo**, com vetores controlados e Qdrant real, sem modelo,
LLM, busca semântica ou participantes. Código da aplicação não foi modificado.

## Separação do parecer EGM

O parecer EGM avaliou clareza, proporcionalidade e limites do desenho documentado.
Não executou este teste. Esta execução fornece evidência funcional específica,
não aprovação semântica, demonstração de valor, cobertura de todos os modos de
falha ou integração da API. As limitações de estado canônico, lock cooperativo,
acesso direto e autorização humana continuam válidas. Relatórios EGM e especificação
não foram reescritos para incorporar resultados retrospectivamente.

## Pré-conferência e escopo

O comando da especificação corresponde ao código e aos caminhos atuais, mas seu
cenário validate não injeta falha parcial. Por isso, além da CLI existente, foi
usado um roteiro temporário de teste fora do repositório, que chama o componente
sem alterá-lo e interrompe um processo após atualizar somente um chunk.

Antes das escritas: os dois nomes de coleção, seus diretórios de estado e
`working/document-control-results/validation-001/` estavam livres. Qualquer nome
ocupado teria impedido a execução. O manifesto aprovado e os hashes dos materiais
foram conferidos. Somente vector-db foi iniciado com `docker compose up -d
--no-deps vector-db`; ai-app e Mock Services não foram iniciados/reconstruídos.
A imagem existente foi usada, com projeto montado somente leitura.

Coleções criadas, mantidas ao final, sem excluir ou substituir coleções anteriores:

- `runbook_chunks_v2_checkout_validation_active_001`: 8 chunks, 4 de RB-V2-001
  ativo versão 1.0, 4 de RB-V2-002 não confirmado versão 0.7.
- `runbook_chunks_v2_checkout_validation_transition_001`: mesmos 8 chunks iniciais;
  RB-V2-001 terminou descontinuado na revisão de classificação 4, somente no teste;
  RB-V2-002 permaneceu não confirmado, revisão 1.

Nenhuma coleção `runbook_chunks_v2_checkout` de carga com embeddings foi criada.
A classificação documental recebida de Marina e os arquivos do lote não mudaram.
As mudanças técnicas de status ocorreram exclusivamente na segunda coleção nova.

## Comandos executados

Validação principal, código de saída **0**:

```bash
docker run --rm --network ai-incident-operations-assistant_default \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/ai-incident-operations-assistant,target=/workspace,readonly \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data,target=/data \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
  ai-incident-operations-assistant-ai-app \
  python /workspace/experiments/document_control.py validate \
  --source-dir /data/working/materials --qdrant-url http://vector-db:6333 \
  --state-dir /data/working/document-control \
  --output-dir /data/working/document-control-results/validation-001
```

Roteiro complementar de falha parcial, código de saída geral **0**:

```bash
docker run --rm --network ai-incident-operations-assistant_default \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/ai-incident-operations-assistant,target=/workspace,readonly \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data,target=/data \
  --mount type=bind,source=/private/tmp/v2_partial_failure_validation.py,target=/partial-validation.py,readonly \
  --env PYTHONDONTWRITEBYTECODE=1 --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
  ai-incident-operations-assistant-ai-app python /partial-validation.py
```

O script usado foi arquivado nos resultados como partial-failure-harness-used.py;
não é novo módulo de produção nem trilha automática de audit. Pré/pós-conferências
foram somente leitura. Reexecutar os comandos com os mesmos destinos agora deve
parar por ocupação, não sobrescrever ou limpar para repetir o resultado.

## Evidências funcionais

### Filtro antes do top 3

Vetores: ativos `[0.8, 0.6]`, inelegíveis `[1.0, 0.0]`, consulta `[1.0, 0.0]`;
coleções com duas dimensões e distância cosseno. Top 3 e limiar 0,50 preservados.
Pontuações são controladas para verificar elegibilidade, não qualidade textual.

| Consulta na coleção ativa | IDs retornados | Scores | Classificação |
|---|---|---|---|
| Sem filtro, limite 3 | RB-V2-002@0.7:04, :03, :01 | 1,0 cada | unconfirmed |
| Pelo componente, filtro antes do limite 3 | RB-V2-001@1.0:02, :04, :01 | 0,8 cada | active |

Apesar da pontuação superior dos inelegíveis, o componente retornou três ativos,
não uma lista vazia obtida ao descartar os três primeiros posteriormente.

### Limites e pacote

- Limites: `RB-V2-001@1.0:04`, seção Limites, documento RB-V2-001, versão 1.0.
- Orientação recuperada e Limites pertencem a RB-V2-001/1.0; metadados preservados
  no ClassifiedPackage, document_policy_version 1.0.
- Uma cópia de contexto com versão 0.7 nos Limites foi rejeitada com
  DocumentIntegrityError: “Versão não corresponde ao catálogo”; nenhum payload
  armazenado foi alterado para esse teste.
- O pacote usa marcador explícito `validation-only-no-persisted-audit-event`.
  Não é audit_event_id de investigação real e nenhum evento JSONL foi criado.
- A CLI também confirmou rejeição de contexto antigo após depreciação e
  encerramento `not_eligible` quando nenhum documento permanece ativo.

### Reclassificação, interrupção e recuperação

Somente na coleção de transição:

1. A CLI carregou ativo/revisão 1 e concluiu a reclassificação técnica para
   deprecated/revisão 2, incluindo todos os chunks e Limites.
2. Para o teste de falha, o componente reativou a versão na coleção de teste,
   revisão 3. Isso não muda a classificação humana ou os arquivos de origem.
3. Um processo filho iniciou transição para deprecated/revisão 4. Após persistir
   blocked e atualizar **um de quatro chunks**, encerrou abruptamente com código
   **73**, intencional. Restaram um deprecated e três active no Qdrant; o estado
   persistente indicava blocked. Não foi apenas uma exceção simulada em memória.
4. Outro processo, com novo executor, tentou busca, Limites e pacote. Todos
   retornaram ControlError “Classificação incompleta: reconciliação explícita
   necessária”. Contador do adaptador mostrou **zero leituras de backend** nessas
   tentativas: o estado bloqueado impediu o fluxo antes de consultar a coleção.
5. Um segundo processo concorrente também não conseguiu adquirir o lock enquanto
   o primeiro o detinha, com erro explícito. Não executou operação na coleção.
6. Somente `reconcile()` explícito aplicou a transição registrada a todos os quatro
   chunks, incluindo Limites, e marcou ready. Resultado: RB-V2-001 deprecated,
   revisão 4; RB-V2-002 unconfirmed, revisão 1, sem mudança.
7. Busca e Limites retornaram listas vazias; contexto antigo foi rejeitado;
   contexto abstido retornou not_eligible/ABSTAINED. Nenhum LLM foi chamado.

Estados anteriores, parciais e finais foram salvos como evidência deste teste;
eles não acrescentam histórico automático ao componente. O teste cobre a
interrupção controlada de processo após uma escrita confirmada no Qdrant, não
queda de energia do host, falha de filesystem ou particionamento de rede.

## Preservação de coleções, dados e V1

Pré/pós-conferência de IDs, payloads, vetores e configuração, com hashes idênticos:

| Coleção preexistente | Pontos preservados | SHA-256 de IDs/payloads/vetores, antes = depois |
|---|---:|---|
| runbook_chunks | 10 | 93db219d7caba0371bbf0fc49f993a3e9c8f83a0880d26003ecbea78b8ce7ab7 |
| experiment_chunks_4b182e19d7eb4935a6d89d1d37577924_a | 11 | cf5a253c348e4c210876accfa36028070affdb046bd4dba45d04de6cc261c50f |
| experiment_chunks_4b182e19d7eb4935a6d89d1d37577924_c | 11 | b1fdcfac74f1e07c133b299001ba2a5cf00e65539274eb0e70431cfa50676f27 |

A listagem final contém exatamente as três anteriores e as duas criadas nesta
execução. Configurações das três anteriores também permaneceram idênticas.
ZIP, 12 arquivos em received e 12 cópias de materials mantiveram seus hashes;
RB-V2-001 ativo e RB-V2-002 não confirmado nos materiais preservados.
Fontes Python de ai-app/experiments coincidem com o snapshot anterior à etapa 8;
projeto montado readonly nos executores. Não foram feitas chamadas à API V1 ou
novos testes de seus endpoints nesta validação. Preservação de dados/código não
é uma nova execução de regressão funcional completa da V1.

## Estado e resultados persistentes

Raiz no host:
`/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data/working/`.

- Estado: `document-control/<nome-da-coleção>/state.json` e executor.lock.
- Resultados: `document-control-results/validation-001/`.
- CLI: request.json, validation.json, result.json.
- Controle: preflight.json, postflight.json, guard-used.py,
  partial-failure-harness-used.py e artifacts-sha256.json.
- Falha/recuperação: subpasta failure-recovery-001 com snapshots do estado/payloads,
  comparação de ranking, pacote, rejeição de versão, código de interrupção,
  prova de bloqueio em novo processo, exclusividade e resultado de reconciliação.

Todos fora do Git. Paths estavam livres; não houve substituição de artefatos de
execuções anteriores. Nenhuma coleção foi excluída. Os estados finais estão ready;
na coleção de transição não há documentos ativos. Vetores das duas coleções são
fixtures técnicas, não índice semântico para uso da aplicação.

## Conclusão e limitações

Resultado funcional favorável para filtro antes do ranking, coerência documental
por versão, reclassificação integral, bloqueio persistente após interrupção,
exclusividade e recuperação explícita nos cenários executados. Não demonstra
sustentação semântica, autorização autenticada, proteção contra clientes externos,
resiliência a todos os modos de falha, integração da API ou ganhos para analistas.

Esforço humano contínuo não medido; não converter duração dos comandos ou
estimativas em horas realizadas. Sem commit ou push. Relatórios e parecer EGM
anteriores preservados; este registro funcional é evidência separada.
