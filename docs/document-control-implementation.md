# Controle documental V2 — implementação e ponto de revisão

Data: 2026-11-05. Entrega técnica no recorte autorizado: checkout, RB-V2-001 ativo,
RB-V2-002 não confirmado. **Parada antes da validação real no Qdrant.**
Não houve carga, consulta ou reclassificação em coleção real nesta entrega.

## Objetivo e fronteira de aceite

Reduzir o risco de orientar o analista com procedimentos não aprovados para uso,
permitindo como fundamento somente documentos explicitamente ativos. O aceite
atual cobre **componente e CLI isolados**, com testes simulados e validação real
separada ainda pendente; não cobre proteção integral da investigação pela API.

A API V1 em `ai-app/main.py` continua usando `search_qdrant.py`, sem adotar
`DocumentControl`. Um futuro consumidor precisará integrar busca, Limites e
montagem de pacote por esse componente, sob o mesmo estado/lock, antes de alegar
proteção de ponta a ponta no fluxo de investigação. Essa integração não foi
realizada ou autorizada automaticamente pelo aceite desta entrega.

## Recorte e materiais do cenário

Checkout é a aplicação de conclusão de compras do cenário. O lote fictício
`SIM-S1D2-001` contém dois procedimentos Markdown, quatro históricos e quatro
recortes de incidentes JSON, além de manifesto com hashes e README. Foi recebido
para inspeção/desenvolvimento, não para baseline ou avaliação final independente.
Marina é a responsável fictícia pela classificação técnica dos procedimentos.

| Material | Identidade e classificação recebidas | Papel nesta entrega |
|---|---|---|
| RB-V2-001 | Procedimento de checkout com timeout na dependência de pagamentos; versão 1.0, revisão 2026-10-20, ativo (`active`) | Fonte elegível candidata. Marina confirmou aplicabilidade inicial a INC-V2-001, preservadas condições e Limites |
| RB-V2-002 | Procedimento legado de falha de resolução de nome; versão 0.7, revisão não informada, status não confirmado (`unconfirmed`) | Teste negativo de restrição; não pode fundamentar orientação. Não é classificado como desatualizado ou descontinuado por inferência |
| INC-V2-001 | Recorte sintético P2 de checkout, janela 2026-11-04 10:00–10:10 UTC, dois timeouts e métricas degradadas no período | Fornece incidente/logs/monitoring para o contexto de teste. Não contém dados de pagamentos nem comprova causa raiz ou necessidade de alterar pool |

O comando de validação usa apenas esses dois procedimentos e os dados do recorte
INC-V2-001. Os históricos do lote não são usados nesse cenário técnico. O marcador
de audit descrito adiante é sintético; não representa investigação persistida.
A simulação de depreciação altera somente a segunda coleção de teste, não a decisão
de Marina, os arquivos recebidos ou suas cópias de trabalho.

## Arquivos da entrega

| Arquivo novo | Responsabilidade |
|---|---|
| `ai-app/document_policy.py` | Contratos classificados, identidade do conteúdo e única regra de elegibilidade |
| `ai-app/document_collection.py` | Estado persistente, lock, carga, reclassificação/reconciliação, busca, Limites e pacote classificados; adaptador Qdrant lazy |
| `experiments/document_control.py` | CLI, preparo fiel do lote aprovado, carga opcional e validação técnica separada |
| `ai-app/test_document_policy.py` | Status explícito, divergência, ausência e ausência de inferência pela idade |
| `ai-app/test_document_collection.py` | Ciclo completo simulado, falhas persistentes, exclusividade entre processos e pacote |
| `ai-app/test_document_control_cli.py` | Executor com backend simulado, origem/reconstrução e artefatos de erro |
| Este documento | Evidências, limites, comando futuro e esforço |

**Nenhum arquivo de implementação existente foi alterado.** Contratos classificados
estendem os existentes e preservam seus metadados, usando a montagem, instruções,
elegibilidade geral e validações da V1. Não foi necessário modificar
`llm_input_models.py`/`llm_input_package.py`, diferente da previsão inicial.
API, Dockerfile, Compose, avaliadores e dados V1 permanecem intactos. Pendências
de planejamento e experimento anterior não pertencem a esta entrega.

## Comportamento entregue

- Status e versão obrigatórios, revisão de classificação e responsável explícitos.
  Data documental ausente fica `null` (= não informado), sem inferir ativo pela idade.
- Somente active consistente com catálogo pode fundamentar. Deprecated e unconfirmed
  consistentes ficam inelegíveis; metadados ausentes, desconhecidos ou divergentes
  são erro, não descarte silencioso.
- A busca aplica filtro de documento/versão/status/revisão **antes de top 3** e
  limiar 0,50. Confere também inventário e payloads; incoerência impede o fluxo.
- Limites devem pertencer à versão ativa. Pacote consulta estado novamente e
  rejeita contexto contaminado ou pronto sem Limites da mesma versão.
- Zero documentos elegíveis permite abstenção/not_eligible; operação falha não vira
  lista vazia. P1 e ausência de logs continuam sem pacote elegível.
- Conteúdo de todos os chunks é conferido por hash, sem misturar versões ou apagar
  dados recebidos. Texto integral é reconstruível a partir das seções preparadas.
- Carga exige coleção e estado novos; recusa sobrescrita. Usa modelo atual somente
  no comando load, com cache local e recusa de excesso de tokens; sem download
  automático nem truncamento. O comando validate não carrega modelo.

### Autoridade, catálogo, payload e aplicação da classificação

São quatro papéis distintos, embora catálogo e estado operacional compartilhem
um arquivo no código atual:

| Elemento | Papel e representação efetiva |
|---|---|
| Classificação autorizada por Marina | Decisão humana registrada para este lote: documento/versão e uso permitido. Não é inferida pelo texto, idade ou score; uma string com o nome da responsável não comprova sua autorização |
| Catálogo | Inventário de registros `Classification`, com documento, versão, status, responsável, revisão da classificação, IDs e hashes esperados. É a referência local usada por `eligible` para conferir chunks; fica em `state.json.records`, não em um segundo arquivo de catálogo |
| Metadados dos chunks | Cópia da decisão aplicada ao payload de cada trecho: `document_version`, `document_status`, `classification_revision`, `classified_by` e `review_date`, além dos campos de origem/conteúdo. Devem concordar com o catálogo; não são autoridade humana independente |
| Estado da aplicação | O mesmo `state.json` vincula coleção/endpoint e registra `phase` (`blocked`/`ready`) e `operation`. Na reclassificação guarda também `previous_records`; enquanto bloqueado, `records` descreve o destino da mudança, ainda não uma aplicação concluída |

`DocumentControl.load` monta o catálogo a partir dos chunks preparados, grava
estado bloqueado, carrega e confere os payloads, e só então grava `ready`.
`reclassify` incrementa a revisão da classificação, registra catálogo anterior e
destino sob bloqueio; `reconcile` aplica a transição registrada e verifica todo o
inventário antes de liberar uso. `ready` significa classificação aplicada e
conferida, não aprovação de orientação ou prontidão de avaliação com participantes.

**Limite entre autorização e mecanismo, conferido no código:** `prepare` em
`experiments/document_control.py` verifica o hash do manifesto aprovado, mas usa
uma tabela explícita das duas classificações recebidas; não lê uma decisão humana
assinada nem um catálogo externo de autorização. `load` aceita os metadados de
entrada; `reclassify` recebe status e `classified_by` do chamador, sem autenticar
Marina ou exigir comprovante da nova decisão. Portanto, o componente garante
consistência com o catálogo persistido, **não comprovação automática da autorização
humana**. Só aplicar reclassificação real com decisão registrada e operador
controlado; essa condição operacional não deve ser apresentada como validação
implementada de identidade/permissão. Nenhum mecanismo foi corrigido nesta revisão.

### Limites, contexto e elegibilidade do pacote

**Limites** são os trechos da seção documental chamada `Limites`, que descreve
restrições de interpretação e ação do procedimento, por exemplo não concluir
causa raiz pelo timeout nem reiniciar automaticamente. Não são o limiar de busca
ou limite de tokens. `document_limits` contém esses trechos sem score atribuído.
O contexto reúne incidente, evidências atuais, históricos e documentação; o pacote
separa esse contexto das instruções oficiais para uma futura geração, sem chamá-la.

Fluxo documental previsto para o consumidor do componente:

1. **Busca:** sob estado/lock, conferir catálogo e payloads; filtrar versões ativas
   antes do top 3/limiar 0,50; validar retornos sem descartar inconsistências.
2. **Limites da mesma versão:** para cada documento/versão recuperado, obter somente
   trechos ativos com seção `Limites`. No código atual, `limits` faz essa seleção
   localmente depois da leitura/conferência integral da coleção, não por uma
   consulta filtrada de Limites no servidor Qdrant.
3. **Contexto:** reunir resultados e Limites com as evidências. A decisão herdada
   `evaluate_context` retorna `NO_DOCUMENTATION` se não há documentação,
   `MISSING_DOCUMENT_LIMITS` se falta documento nos Limites, ou `CONTEXT_READY`.
   Essa função compara IDs de documento, não versões ou status.
4. **Elegibilidade do pacote:** `DocumentControl.package` relê estado e confere
   elegibilidade dos chunks; para `CONTEXT_READY` exige Limites também por versão.
   Delega consistência, instruções e encerramentos gerais a `build_llm_input_package`
   da V1. Resultado elegível é um `ClassifiedPackage` com metadados preservados;
   abstenção é `PackageNotEligible`, status `not_eligible`. Contexto declarado pronto
   mas inconsistente gera erro; falha operacional não vira abstenção.

Da V1 são herdados os contratos centrais, validação de mensagem de log preenchida,
coerência do contexto, política/instruções e inelegibilidade de P1, falta de logs e
abstenções. Contexto elegível não significa sustentação semântica aprovada.
Na API V1, P1 interrompe a coleta antes das demais consultas; falta de mensagem
encerra antes de comparação histórica/busca. **Diferença do componente isolado:**
`DocumentControl.package` lê/confere o estado documental antes de delegar os retornos
P1 ou falta de logs. Assim, estado indisponível pode gerar erro antes de devolver
`not_eligible`; não alegar que esse método reproduz a ordem de coleta da API.
O executor de validação monta um contexto técnico a partir do lote; não substitui
a orquestração da API nem implementa a coleta completa da investigação.

### Estado persistente e exclusividade

Cada coleção usa um diretório compartilhado por todos os executores, com
`state.json` e `executor.lock`. Endpoint e coleção ficam vinculados ao estado.
Toda operação exige lock exclusivo `flock` não bloqueante e consulta de estado;
leitura/consulta e montagem de pacote também respeitam o lock. Uma segunda execução
falha antes de qualquer operação no backend. O cliente Qdrant é criado sob demanda.

A operação grava phase=blocked com sincronização antes de alterar a coleção.
Reclassificação registra classificação anterior e destino; atualiza todos os
chunks da versão, incluindo Limites, e só libera após verificar todo o inventário.
Exceção/reinício preserva blocked. Reconciliação exige comando explícito e aceita
apenas a transição registrada; não repara conteúdo desconhecido. Carga interrompida
permanece bloqueada e exige investigação, não tem retry/limpeza automática.

O lock sozinho é liberado com a morte do processo; o bloqueio em state.json não.
Nenhum estado real foi criado ainda. Os testes usam diretórios temporários
`/var/tmp` dentro do container, descartados; o estado real proposto abaixo fica
fora de `/tmp` e do repositório.

**Limite operacional:** todos os clientes deste fluxo devem montar o mesmo
filesystem/estado canônico. Cliente que acesse Qdrant diretamente ou use outro
diretório para a mesma coleção contorna o controle; não há ACL/revogação no servidor
nesta fatia. Verificação integral da pequena coleção a cada operação privilegia
consistência, não escalabilidade. Não há promessa de atomicidade multi-registro
no Qdrant: o estado bloqueado impede exposição da atualização parcial.

### Retenção do estado e rastro das reclassificações

Conferência estática de `DocumentControl.reclassify`/`reconcile`, da CLI e de
`ai-app/audit.py`, em 2026-11-05; nenhuma reclassificação foi executada nesta revisão.

Após uma reclassificação concluída, `state.json` mantém coleção/endpoint,
`phase="ready"`, `operation="reclassify"`, `records` com o catálogo vigente e
`previous_records` com o catálogo inteiro imediatamente anterior à última
reclassificação. A versão alterada recebe status/responsável informados pelo
chamador e revisão de classificação incrementada. A conclusão muda phase para
ready, sem remover previous_records ou acrescentar um evento histórico.

Portanto, a classificação anterior **é preservada como um único snapshot anterior**,
não como histórico acumulado. Na próxima reclassificação, mesmo de outro documento,
previous_records é substituído pelo catálogo vigente antes dessa nova operação;
records recebe o novo destino. Há o catálogo atual e um predecessor global, não
uma sequência por documento. A gravação atômica substitui o arquivo: o arquivo
intermediário `.pending` não constitui backup ou log histórico. Não são registrados
no estado timestamp da decisão, motivo ou referência ao comprovante de autorização.

Para comandos de carga/reclassificação/reconciliação da CLI, o diretório novo de
resultados registra `request.json` com os argumentos e, no sucesso, `result.json`
com a operação e uma cópia do estado lido após sua conclusão. Erros capturados
produzem `error.json` com tipo/mensagem; interrupção ou falha de escrita pode deixar
artefatos incompletos. A validação técnica grava também `validation.json`, com
resultados das coleções e verificações, não um diário completo de classificações.
Chamadas diretas ao componente não criam esses relatórios da CLI automaticamente.

**Reconstrução:** somente state.json permite examinar o estado atual e a última
transição representada, não todas as mudanças. Diretórios da CLI preservados podem
ajudar a comparar snapshots e revisões, mas não há índice/encadeamento de execuções,
registro append-only, prova de completude, autenticação do responsável ou garantia
de sequência temporal. Operações diretas, artefatos ausentes e novas transições
limitam a reconstrução. `classified_by` identifica o valor declarado pelo operador,
não comprova que Marina autorizou. O vínculo com a decisão humana depende dos
registros documentais do exercício; não há referência obrigatória a eles no estado.

Esse mecanismo é **estado operacional com um predecessor**, não uma trilha nova de
auditoria. O audit da investigação é separado: `ai-app/audit.py` grava eventos JSONL
com event_id, timestamp, incidente, etapa e referências recuperadas/correspondentes.
O controle documental não acrescenta ali eventos de carga/reclassificação, e seu
método `audit` apenas confere coleção/catálogo, sem gravar esse JSONL. Não usar
audit_event_id da investigação como prova de histórico de classificação inexistente.
Nenhuma trilha adicional foi implementada para encerrar o achado.

## Decisão arquitetural e alternativas

**Decisão aprovada pelo usuário no papel de responsável pelo projeto, em
2026-11-05:** manter catálogo e estado local persistente com lock para o executor
V2 isolado. Esta é uma **justificativa retrospectiva, formulada após a
implementação**, não evidência de que todas as alternativas foram avaliadas antes
de construir o componente. A decisão não amplia escopo, dados ou garantias.

Os custos abaixo são **estimativas qualitativas de implementação/operação**, não
horas medidas, benchmarks ou comparação experimental. As alternativas não foram
construídas para esta avaliação.

| Alternativa | Adequação ao executor local e custo qualitativo | Falhas parciais e recuperação | Concorrência |
|---|---|---|---|
| Status somente nos payloads do Qdrant | Menor complexidade inicial, mas insuficiente sozinho para o controle requerido | Pode deixar chunks divergentes; requer mecanismo adicional para detectar e bloquear aplicação incompleta | Não coordena escritores por si só |
| Catálogo e estado local persistente com lock — escolha atual | Custo moderado; utiliza filesystem e execução local existentes | Bloqueio persistente impede uso até conferência/reconciliação explícita; depende de preservar o estado. Carga interrompida exige investigação | Serializa operações que compartilham o estado canônico; clientes externos podem contornar o componente |
| Nova coleção por revisão, com troca de referência | Maior custo de preparação, armazenamento e gestão de coleções | Permite conferir uma revisão antes de disponibilizá-la; exige controlar troca de referência, falhas na publicação e coleções remanescentes | Pode manter leitores na revisão anterior; publicação e escritores ainda precisam de coordenação |
| Banco transacional para catálogo e operações | Maior custo de infraestrutura e operação neste recorte | Transações protegem registros no banco, mas não tornam automaticamente atômicas as escritas no Qdrant; coordenação e recuperação continuam necessárias | Facilita coordenação entre processos; não resolve sozinho a consistência entre banco e Qdrant |

A escolha é proporcional a um executor local, lote pequeno e indisponibilidade
aceitável durante atualização/recuperação. Ela prioriza impedir uso de uma
classificação parcialmente aplicada. Payloads isolados não resolvem esse requisito;
gestão de coleções por revisão e outro serviço transacional acrescentam custo sem
necessidade demonstrada no recorte atual. Permanecem alternativas de evolução,
não soluções descartadas para qualquer contexto futuro.

**Condições de validade:** todos os acessos controlados usam o componente e o
mesmo diretório persistente canônico; operações são serializadas; bloqueios ficam
visíveis; recuperação é explícita e consultas podem ficar indisponíveis durante
reclassificação. O lock não autentica Marina nem impede acesso direto ao Qdrant.
O catálogo e o estado compartilham o arquivo para essa pequena unidade local de
controle; essa decisão não acrescenta fonte independente de autorização humana.

**Gatilhos de reavaliação:** escritores independentes que não compartilhem o lock;
réplicas ou execução distribuída sem estado canônico comum; necessidade de
consultar durante reclassificações; contenção ou custo de conferência integral
incompatíveis com o volume; exigência de autorização/trilha de decisões mais forte.
Nenhum limite quantitativo de escala foi medido ou estabelecido nesta entrega.

Ao surgir um gatilho, reavaliar com o responsável pelo projeto antes de ampliar o
uso. Publicação por revisão pode atender à continuidade de leitura; coordenação
transacional pode atender a operações distribuídas. A escolha dependerá da
necessidade e dos trade-offs demonstrados, sem migração automática ou promessa de
atomicidade com o Qdrant. Por ora, mantêm-se a implementação e suas limitações.

## Testes executados

Docker Desktop estava parado; foi iniciado após autorização explícita do usuário.
Não houve rebuild nem comando de restart/alteração dos serviços Compose.
Imagem existente: `ai-incident-operations-assistant-ai-app`, ID
`sha256:4d77d677f7cd16ab3954b29a0897ab3a4ab70e8568c6af556aa8608f3168b962`.

Comando final executado:

```bash
docker run --rm --network none \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/ai-incident-operations-assistant,target=/workspace,readonly \
  --workdir /workspace/ai-app \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --env HF_HUB_OFFLINE=1 --env TRANSFORMERS_OFFLINE=1 \
  ai-incident-operations-assistant-ai-app \
  python -m unittest -v \
  test_document_policy test_document_collection test_document_control_cli \
  test_llm_input_package test_context_rules test_document_limits_failure
```

**Resultado: 55 testes aprovados, código 0**, mais quatro cenários assertivos de
`test_context_rules` executados na importação desse arquivo. São 30 testes novos
(5 política, 20 controle, 5 CLI) e 25 regressões da V1 (24 pacote, 1 falha Limites).
A duração informada pelo runner final foi 0,265 s; não representa esforço humano.
Mensagens ERRO dos testes da CLI são resultados esperados dos cenários negativos.

Cobertura inclui ativo→descontinuado em todos os chunks/Limites, contexto antigo
rejeitado, bloqueio após reinício, reconciliação explícita, duas execuções em
processos distintos, payload inválido, filtro antes do limite, preservação de
texto/metadados e regressões P1/logs/abstenção/HTTP 503 de Limites. Sem rede,
embeddings, Qdrant ou audit real. Não houve descoberta geral de testes.

## Validação real proposta — NÃO EXECUTADA

O próximo comando criará somente:

1. `runbook_chunks_v2_checkout_validation_active_001`
2. `runbook_chunks_v2_checkout_validation_transition_001`

As duas usam os mesmos textos/classificações iniciais do lote; vetores controlados
de duas dimensões dão pontuação maior aos inelegíveis para provar filtro antes do
ranking. Isso é teste de controle documental, **não avaliação de embedding ou busca
semântica**. A segunda coleção simula depreciação de RB-V2-001 só nos registros de
teste; não modifica arquivos/classificações do lote, nem a primeira coleção.

O executor monta contexto/pacote de teste com dados existentes de INC-V2-001 e
marcador explícito `validation-only-no-persisted-audit-event`; não é um event_id
real e não grava audit. A preservação de audit_event_id real fornecido é verificada
nos testes isolados. Não há geração ou participação de analistas.

Estado persistente no host:
`/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data/working/document-control/<nome-da-coleção>/`.
Cada subdiretório terá `state.json` e `executor.lock`.
Resultados novos no host:
`/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data/working/document-control-results/validation-001/`.
Arquivos: `request.json`, `validation.json`, `result.json` ou `error.json`.
Destinos existentes não são sobrescritos; coleções existentes não são excluídas.

Comando exato para revisão, ainda não executado:

```bash
docker run --rm \
  --network ai-incident-operations-assistant_default \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/ai-incident-operations-assistant,target=/workspace,readonly \
  --mount type=bind,source=/Users/renatodanielbrito/Documents/Git/AI-Incident-POC-V2-Data,target=/data \
  --workdir /workspace \
  --env PYTHONDONTWRITEBYTECODE=1 \
  ai-incident-operations-assistant-ai-app \
  python /workspace/experiments/document_control.py validate \
  --source-dir /data/working/materials \
  --qdrant-url http://vector-db:6333 \
  --state-dir /data/working/document-control \
  --output-dir /data/working/document-control-results/validation-001
```

Pré-condição: serviço vector-db e rede Compose existentes disponíveis. Não foi
iniciado para este teste. O comando acima não cria `runbook_chunks_v2_checkout`
em si nem carrega embeddings oficiais/experimentais preexistentes. A carga com
embeddings está implementada em load, mas não será executada ou implicitamente
acoplada à validação de controle; exige etapa posterior revisada.

## Esforço e estado de revisão

**Esforço humano efetivo não medido continuamente.** Não registrar as 30 h da
estimativa como realizadas nem inventar horas a partir da duração dos comandos.
Houve implementação, revisão estática, duas rodadas direcionadas de teste
(53 e depois 55 testes) e espera pelo runtime Docker. Nenhum apontamento adicional
de Marina, consumo de reserva ou resultado de baseline foi presumido.

Entrega preparada para revisão antes da validação real. Sem commit ou push.
