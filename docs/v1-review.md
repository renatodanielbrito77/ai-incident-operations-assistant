# Revisão da V1 — AI Incident Operations Assistant

Data: 2026-11-03. Base de código conferida até o commit `4c852bf`.
Este documento registra o estado entregue da POC local, sem declarar prontidão
para produção ou aprovação de conteúdo gerado.

**Nesta revisão: não executar descoberta geral de testes, novas investigações,
gerações, evals reais, preparação de índices ou alterações de código.** Os
comandos abaixo são um roteiro para execução posterior, não ações realizadas
para escrever este documento. Nenhum serviço foi reiniciado.

## 1. Resultado entregue e fronteira da V1

O projeto permite demonstrar uma investigação determinística, com evidências,
históricos, recuperação documental e correlação de audit. Uma CLI experimental
compõe esse resultado com geração local de candidata e relatório para revisão
humana. A API continua retornando contexto, escalonamento ou solicitação de dados;
a geração não foi integrada ao endpoint.

O objetivo documentado no [README](../README.md) é aprender e construir uma POC
local de apoio à investigação. Não foi localizado um documento versionado com
critérios formais de fechamento de todo o objetivo original ou aceite de
Negócios. Portanto, fluxo técnico demonstrado, aceite de V1 e atendimento a uma
demanda operacional real não devem ser tratados como equivalentes.

### Fluxo entregue

| Etapa | Comportamento implementado | Referência |
|---|---|---|
| Investigação | `POST /investigate/{incident_id}` consulta o incidente nos Mock Services. | [main.py](../ai-app/main.py) |
| P1 | Persiste evento e retorna escalonamento manual antes de consultar históricos, monitoring e logs. Não envia notificação nem aciona uma equipe. A CLI encerra sem LLM. | [main.py](../ai-app/main.py), [CLI](../experiments/investigate_and_report.py) |
| Evidências atuais | Para não-P1, coleta históricos, monitoring e logs. Se nenhuma mensagem tiver texto após `strip()`, solicita dados adicionais, sem comparar históricos ou consultar documentação. | [evidence_rules.py](../ai-app/evidence_rules.py) |
| Históricos | Mock filtra por aplicação e retorna todos os registros encontrados. A comparação textual usa `strip().casefold()` e igualdade do texto completo, sem score semântico; preserva recuperados e correspondências separadamente. | [Mock](../mock-services/main.py), [history_rules.py](../ai-app/history_rules.py) |
| Recuperação documental | A consulta combina aplicação, resumo e mensagens de logs; busca na coleção oficial `runbook_chunks`, `top_k=3`, limiar `0.50`. Acrescenta Limites por filtro de documento/seção, paginado, sem score. | [search_qdrant.py](../ai-app/search_qdrant.py) |
| Decisão documental | Ausência de documentação ou de Limites por documento gera abstenção. Presença de ambos gera `CONTEXT_READY`, sem comprovar causa raiz ou suporte semântico completo. | [context_rules.py](../ai-app/context_rules.py) |
| Audit | Append JSONL antes da resposta de negócio. Retorna o mesmo `event_id` como `audit_event_id`; registra etapa, chunks, históricos recuperados e correspondentes e status da comparação. | [audit.py](../ai-app/audit.py) |
| Pacote | Montagem pura reutiliza contratos independentes de `main.py`. P1, falta de logs e abstenções são inelegíveis; contexto declarado pronto inconsistente gera validação distinta. Preserva conteúdo, ordem e ID. | [investigation_models.py](../ai-app/investigation_models.py), [llm_input_models.py](../ai-app/llm_input_models.py), [montagem](../ai-app/llm_input_package.py) |
| Geração local | Somente pacote elegível permite uma chamada ao Ollama. Usa instruções oficiais, schema de candidata e barreiras de conclusão/limites. Não repara, repete, aumenta limites ou executa ações. | [executor](../experiments/send_package_to_ollama.py), [CLI](../experiments/investigate_and_report.py) |
| Verificações estruturais | Pydantic valida formato; regras separadas conferem presença de referências e tipo declarado. Permite apenas `observe` e `request_verification`; não confronta texto com tipo ou chunks. | [modelos](../ai-app/recommendation_models.py), [regras](../ai-app/recommendation_rules.py), [composição](../ai-app/recommendation_structure.py) |
| Relatório | Candidata e relatório estrutural válidos usam o gerador existente, incluindo rejeição estrutural. Erros e inelegibilidade recebem resumo próprio, sem fabricar esses objetos. | [gerador](../ai-app/recommendation_report.py), [CLI](../experiments/investigate_and_report.py) |

A geração e o relatório reutilizam o ID da investigação. Não geram novos IDs de
audit nem acrescentam eventos da geração ao JSONL. Modelo, parâmetros, resposta
bruta e resultado ficam nos artefatos da CLI. Assim, a correlação existe, mas o
audit da API não é um registro integral de todas as atividades posteriores.

O juiz semântico é um experimento separado, não chamado pela CLI e não usado
como autorização. `semantic_support_status` das verificações estruturais continua
`not_evaluated`.

## 2. Como demonstrar

### Pré-condições

Executar a partir da raiz do repositório, em um ambiente previamente preparado:

- Docker/Compose disponíveis, imagem `ai-incident-operations-assistant-ai-app`
  existente e os serviços `ai-app`, `mock-services` e `vector-db` em execução.
- Base oficial `runbook_chunks` já populada. Subir o Compose não cria ou carrega
  automaticamente essa base. A preparação descrita no README gera dados e grava
  no Qdrant; não é parte deste roteiro de revisão.
- Embeddings da API disponíveis e inicialização concluída. O Ollama roda no Mac,
  com `qwen3:1.7b` já instalado. Não baixar modelos para esta demonstração sem
  tratar essa preparação separadamente.
- Recursos suficientes para o modelo e containers. Os experimentos de compatibilidade
  foram feitos no Ollama `0.40.14`; a CLI não consulta automaticamente sua versão.

As URLs são configuráveis. `127.0.0.1` dentro do container aponta para ele mesmo:
na rede do Compose usar `http://ai-app:8000`; para Ollama no Mac usar
`http://host.docker.internal:11434`.

### Comandos reproduzíveis, sem build ou reinício

Criar uma raiz nova para os resultados; cada diretório de incidente deve ainda
não existir. O caminho abaixo é apropriado ao ambiente macOS utilizado:

```bash
V1_DEMO_ROOT="$(mktemp -d /private/tmp/v1-demo.XXXXXX)"
```

Primeiro P1, depois aplicação sem documentação:

```bash
docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace:ro" -v "$V1_DEMO_ROOT:/review" -w /workspace ai-app \
  python -B experiments/investigate_and_report.py \
  --incident-id INC-002 --api-url http://ai-app:8000 \
  --ollama-url http://host.docker.internal:11434 --output-dir /review/INC-002

docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace:ro" -v "$V1_DEMO_ROOT:/review" -w /workspace ai-app \
  python -B experiments/investigate_and_report.py \
  --incident-id INC-003 --api-url http://ai-app:8000 \
  --ollama-url http://host.docker.internal:11434 --output-dir /review/INC-003
```

Somente depois conferir esses resultados e executar o caso elegível:

```bash
docker compose run --rm --no-deps --pull never \
  -v "$PWD:/workspace:ro" -v "$V1_DEMO_ROOT:/review" -w /workspace ai-app \
  python -B experiments/investigate_and_report.py \
  --incident-id INC-001 --api-url http://ai-app:8000 \
  --ollama-url http://host.docker.internal:11434 --output-dir /review/INC-001
```

Esses comandos fazem investigações reais e, para INC-001 elegível, uma chamada
real ao Ollama. A API grava os eventos normais de audit. Não fazem preparação do
índice, build ou reinício. Cada execução nova produz novos IDs de audit; os IDs
registrados nos relatórios não devem ser esperados em uma repetição.

| Caso | Resultado de referência | Código | `candidate_produced` | Ollama |
|---|---|---:|---|---|
| INC-002 | `NOT_ELIGIBLE`, motivo `P1` | 0 | `false` | Não chamar |
| INC-003 | `NOT_ELIGIBLE`, motivo `ABSTAINED`; API `NO_DOCUMENTATION` | 0 | `false` | Não chamar |
| INC-001 | Pacote elegível; na validação registrada, `STRUCTURAL_CHECKS_PASSED` | 0 na execução registrada | `true` na execução registrada | Uma chamada |

O conteúdo e a passagem estrutural de uma nova geração de INC-001 não são
resultados garantidos. O script para se houver erro, conclusão incompleta,
limite atingido ou saída inválida; não deve ser repetido automaticamente para
obter um resultado favorável. Mudanças no índice podem alterar a elegibilidade.

### O que conferir nos artefatos

Em `$V1_DEMO_ROOT/INC-xxx`: `parameters.json`, `result.json`, `report.md` e
`investigation/response.body` com seus metadados. Somente o caminho elegível gera
`package.json` e `generation/`, com requisição, resposta bruta e resultados.

- Ler `final_state`, `reason_code`, `candidate_produced` e `generation_attempted`.
  Código 0 também significa encerramento normal sem candidata.
- Conferir `audit_event_id` entre resposta de investigação, resultado e pacote,
  quando este existir. A leitura do JSONL para confirmar exatamente um evento
  correspondente foi feita na validação controlada; não é uma busca automática
  implementada na CLI. Não expor o arquivo inteiro para demonstrar a correlação.
- Conferir modelo, parâmetros, política, `done_reason`, contagens e relatório.
  Um parâmetro de modelo registrado num caso inelegível não significa uso do LLM.
- Ler a candidata e os trechos citados. Passagem estrutural não encerra a revisão.

| Estado final da CLI | Código | Distinção |
|---|---:|---|
| `STRUCTURAL_CHECKS_PASSED` | 0 | Candidata para revisão humana |
| `NOT_ELIGIBLE` | 0 | P1, falta de logs ou abstenção; sem LLM |
| `STRUCTURAL_CHECKS_FAILED` | 1 | Candidata bem formada, rejeitada por referências/política |
| `INVESTIGATION_FAILED` | 2 | Transporte ou HTTP de erro da investigação |
| `CONTEXT_INVALID` | 2 | Resposta/contexto inconsistente, não inelegibilidade legítima |
| `GENERATION_FAILED` | 2 | Falha operacional, limite ou saída inválida da geração |
| `ARTIFACT_FAILED` | 2 | Falha de diretório, gravação ou apresentação |

## 3. Validação disponível

Nenhum teste ou avaliador foi executado nesta revisão documental. Os registros
abaixo descrevem evidências existentes, não uma certificação global da suíte.

### Testes isolados

| Camada | Arquivos e cobertura disponível |
|---|---|
| API, audit e falhas | [test_audit_event_id.py](../ai-app/test_audit_event_id.py), [test_audit_historical_ids.py](../ai-app/test_audit_historical_ids.py), [test_document_limits_failure.py](../ai-app/test_document_limits_failure.py): respostas, P1, logs, erros por etapa, históricos e JSONL temporário. Substituem `search_qdrant` antes da importação. |
| Regras puras | [test_evidence_rules.py](../ai-app/test_evidence_rules.py), [test_history_rules.py](../ai-app/test_history_rules.py); [test_context_rules.py](../ai-app/test_context_rules.py) é um script explícito de asserções, não uma suíte unittest convencional. |
| Contratos, referências, ações e apresentação | `test_recommendation_models.py`, `test_recommendation_rules.py`, `test_recommendation_actions.py`, `test_recommendation_structure.py`, `test_recommendation_report.py`, em `ai-app/`. |
| Pacote | [test_llm_input_package.py](../ai-app/test_llm_input_package.py): elegibilidade, consistência, preservação, serialização e ausência de import de embeddings/API. |
| Evals | `test_eval_retrieval.py`, `test_eval_document_context.py`, `test_eval_candidates.py`, em `ai-app/`, com resultados simulados. Testam executores; não medem recuperação real. |
| Mock | [test_historical_incidents.py](../mock-services/test_historical_incidents.py): filtro, contrato, ordenação e ausência de histórico. |
| CLI e geração | [test_investigate_and_report.py](../experiments/test_investigate_and_report.py) e [test_send_package_to_ollama.py](../experiments/test_send_package_to_ollama.py): 40 testes passaram na revisão da entrega, sem rede. |
| Juiz experimental | [test_judge_claim_examples.py](../experiments/test_judge_claim_examples.py): 21 novos testes; junto aos 20 do transporte, 41 passaram na entrega. Valida isolamento de rótulos e referências; não comprova correção semântica. |

Exemplo de seleção explícita, sem rede, para a CLI já entregue:

```bash
docker run --rm --network none \
  --mount "type=bind,source=$PWD,target=/workspace,readonly" \
  --workdir /workspace/experiments ai-incident-operations-assistant-ai-app \
  python -B -m unittest -q test_investigate_and_report test_send_package_to_ollama
```

Não somar os registros de 40 e 41 como testes únicos: ambos incluem os mesmos 20
testes do transporte. Não usar `unittest discover`, descoberta do pytest ou
execução indiscriminada de `test_*.py`: existem scripts que carregam modelos,
criam coleções, gravam audit ou acessam serviços, incluindo `test_qdrant.py`,
`test_search.py`, `test_limits.py`, `test_embedding.py` e `test_audit.py`.

### Integrações reais registradas

- [Validação da CLI](../experiments/investigate_and_report_validation.md): INC-002
  e INC-003 sem LLM; INC-001 com uma chamada, 11,931 s, 1.887 tokens de entrada e
  172 de saída, `stop`. Respostas correlacionadas a exatamente um evento por ID;
  pacote e evidências preservados. O driver temporário contou e limitou chamadas.
- A candidata passou estruturalmente, mas a revisão encontrou dados faltantes
  não delimitados, condição de recorrência omitida e restrição dos Limites usada
  sem citar `RB-001-05`. Não foi identificado uso indevido explícito dos históricos.
- [Três experimentos de geração](../experiments/ollama_candidate_experiments_report.md):
  instruções oficiais, instruções adicionais e orçamento de saída maior. E2 foi
  rejeitado pela barreira conservadora ao atingir 256 tokens, apesar de `stop`;
  E3 retornou o mesmo texto com teto 512 e passou estruturalmente. Nenhuma variante
  foi promovida automaticamente à política oficial.
- [Juiz semântico](../experiments/claim_judge_experiment_report.md): duas saídas
  válidas, uma concordância e uma divergência, além de uma saída rejeitada por
  combinar abstenção e classificação preenchida. Não há taxa geral de qualidade.
  O caso inválido não foi reparado nem comparado ao rótulo humano.

Falhas de audit, contexto incompleto, falta de logs e rejeições estruturais têm
cobertura isolada; não foram todas exercitadas na última rodada real da CLI.
Registros de integração não substituem testes de todos os caminhos de falha.

### Evals e experimentos de recuperação

- [retrieval_cases.json](../evals/retrieval_cases.json): **seis casos**, RET-001 a
  RET-006. Expectativas representam o comportamento desejado, sem ajuste para
  copiar resultados atuais.
- [eval_retrieval.py](../ai-app/eval_retrieval.py): busca vetorial. Para retrieve,
  exige todos os IDs esperados; para abstain, nenhum resultado.
- [eval_document_context.py](../ai-app/eval_document_context.py): mesmos casos,
  mas avalia a união da busca com Limites por documento, sem score para o filtro.
  Ambos fixam `top_k=3`, `min_similarity=0.50` e separam reprovação de erro.
- [candidate_cases.json](../evals/candidate_cases.json) e
  [eval_candidates.py](../ai-app/eval_candidates.py): quatro expectativas de
  estrutura. CAND-003 pode atender à expectativa estrutural e continuar
  contradizendo o runbook segundo a anotação humana.
- [claim_examples.json](../evals/claim_examples.json): três anotações humanas
  rastreáveis à mesma candidata E3. Não são benchmark confiável de juiz semântico.
- [Comparação A/C](../experiments/chunk_embedding_comparison_report.md): ambas
  registraram 4/6 na busca e 5/6 no contexto final. RET-004 falhou; em RET-005 os
  Limites supriram o ID esperado. São **coleções experimentais com 11 trechos**,
  não o índice oficial de dez chunks: esses números não devem ser apresentados
  como resultado atual do índice oficial. A decisão foi manter `runbook_chunks`.

Há executores reais disponíveis, mas não foi feita nova execução nem localizada
uma captura versionada completa dos seis resultados oficiais atuais para afirmar
uma taxa atual de recuperação. Não preencher essa lacuna com números do A/C.

## 4. Limitações aceitas no escopo atual

- **Revisão humana obrigatória para uso do conteúdo.** É uma condição de uso da
  POC, não um workflow de aprovação persistida implementado. O programa não
  executa ações, não notifica escalonamento e não transforma código 0 em aprovação.
- **Juiz semântico experimental sem confiabilidade demonstrada.** Pointers e
  source_ids válidos garantem rastreabilidade, não a sustentação da justificativa.
  A candidata completa pode influenciar o modelo apesar de não ser evidência.
- Um runbook, dez chunks oficiais, seis casos de recuperação, três incidentes e
  três históricos fictícios. Não há validação em diversidade operacional real.
- Históricos usam filtro por aplicação e correspondência textual, não similaridade
  semântica ou comprovação de mesma causa. Uma resolução anterior não é orientação.
- Log não vazio é presença de texto, não qualidade da evidência. Não há validação
  de janela temporal, recorrência ou suficiência causal. Os dados de logs são
  datados, sem garantia de coincidência com o momento da requisição.
- Um timeout não comprova indisponibilidade; `CONTEXT_READY` não comprova causa
  raiz nem dados suficientes para qualquer verificação futura.
- A API carrega embeddings na importação, inclusive antes de receber P1. O retorno
  antecipado evita recuperação e LLM, não o custo inicial desse carregamento.
- Dependências Python e imagem Qdrant não estão fixadas por versão no projeto;
  o ambiente e os resultados podem variar. Há custos de memória e inicialização
  no Mac M2 de 8 GB. Nenhuma capacidade ou latência de produção foi demonstrada.
- Compose não tem healthchecks; base/modelos exigem preparação; o Dockerfile não
  inclui os experimentos, exigindo a montagem do projeto. A CLI reutiliza HTTP
  simples do transporte experimental, sem HTTPS, autenticação ou retries.
- Timeout do Mock é por operação, não global; a CLI usa 30 s para investigação e
  120 s para geração, não um deadline único do fluxo completo.
- Tratamentos específicos da API cobrem conexão/timeout do Mock, comunicação
  documental e escrita de audit. Outros HTTP/payloads/exceções podem produzir
  500; 404 de monitoring/logs não possuem evento específico.
- Audit é append JSONL, sem fsync, rotação, consulta por API ou transação com a
  resposta. Escrita parcial e perda em queda abrupta são possíveis. Eventos de
  geração/relatório não são acrescentados pela CLI.
- A barreira de contexto depende do comportamento da versão/modelo testados; a
  contagem retornada isoladamente não comprova ausência de corte. Não há
  pré-contagem independente do prompt completo nem atualização automática de
  recursos. Chegar ao teto de saída rejeita o resultado mesmo com `stop`.
- Artefatos de demonstração ficam em diretórios temporários, sem retenção formal.
  Separar instruções e evidências não demonstra resistência a prompt injection.

## 5. Divergências entre documentação e implementação

Registradas explicitamente; README, arquitetura e política não foram corrigidos
silenciosamente nesta revisão.

| Fonte | Divergência ou cobertura incompleta | Estado confirmado |
|---|---|---|
| README: afirmações “Não há LLM” e “Não há LLM, geração de respostas” | Generalização desatualizada para o repositório. | Continua verdadeira para a API de investigação; já existem geração local e CLI experimental fora da API. |
| Arquitetura: “Não há LLM, geração de recomendações” | Não distingue API determinística da camada experimental posterior. | Ollama/CLI/relatórios existem; nenhuma ação corretiva foi integrada. |
| Arquitetura: contratos Pydantic atribuídos a `main.py` | Localização desatualizada. | Modelos de investigação estão em `investigation_models.py` e são importados por `main.py`. |
| README e arquitetura: mapa, diagramas e listas de testes/evals | Não cobrem os módulos de candidata, pacote, geração, relatório, juiz e CLI mais recentes. | As listas antigas continuam úteis, mas não são inventário completo. Os diagramas da API não representam o fluxo completo via CLI. |
| Política oficial versus instruções revisadas em experimentos | As instruções adicionais não são a política em uso. | CLI usa `DIRECTIVES` oficiais e teto 256. Alterar automaticamente para a variante de 512 seria mudança não aprovada. |
| Regras de prontidão na API versus validação do pacote | As duas camadas têm alcance diferente, não equivalência de garantia. | `evaluate_context` verifica documentos e existência de Limites por documento; o pacote acrescenta consistência de logs, aplicações, seção Limites e históricos. |
| Fechamento da V1 e demanda de Negócios | Não foi localizado aceite formal ou enunciado versionado da demanda. | O fluxo técnico está demonstrado, mas não permite declarar atendimento integral a uma demanda de Negócios ainda não registrada. |

A mensagem da API “nenhuma recomendação foi gerada” descreve corretamente a etapa
que produziu o contexto. Ela não é contraditória com uma geração posterior pela
CLI; são momentos distintos do fluxo.

## 6. Lacunas versus melhorias opcionais

### O que ainda não está demonstrado em relação ao objetivo

1. **Aceite formal e objetivo de Negócios:** falta registrar o enunciado e os
   critérios que definem sucesso, público e uso pretendido. Sem isso, não é
   possível atestar cobertura integral do objetivo original além da POC técnica.
2. **Qualidade confiável das orientações:** há saídas com condições omitidas e
   afirmações imprecisas mesmo passando estruturalmente. Isso impede tratar a
   POC como recomendação autônoma confiável; o objetivo restrito de apoio com
   revisão humana permanece demonstrável.
3. **Validação representativa:** uma geração na última integração e o conjunto
   reduzido não demonstram desempenho, qualidade ou segurança em operação real.
   Evidências e critérios de aceite representativos ainda faltam para esse uso.

Não reclassificar automaticamente cada limite aceito como requisito faltante da
V1. Se o objetivo original exigia recomendação no endpoint, interface de aprovação,
notificação de escalonamento ou uso em produção, esses itens **não foram
entregues**; não há critério versionado que permita presumir essa exigência.

### Melhorias opcionais, condicionadas à próxima demanda

- Expandir runbooks, casos e integrações reais; busca histórica semântica.
- Melhorar chunking, consulta e orçamento de geração mediante comparação
  controlada, sem alterar expectativas para esconder reprovações.
- Promover uma CLI a produto, adicionar interface/API de candidata ou registrar
  revisão humana, somente se fizer parte da demanda aprovada.
- Fixar versões, healthchecks, cobertura de erros, retenção/consulta/rotação de
  audit, autenticação, HTTPS e observabilidade. Tornam-se requisitos se o próximo
  escopo exigir implantação operacional; não são evidência de entrega atual.
- AWS, Kubernetes e arquitetura agentic não são pré-requisitos implícitos para
  fechar a demonstração local; dependem de justificativa e aceite próprios.

## 7. V2 — pendências explícitas

### Comparação determinístico versus agentic — pendente

Ainda não há implementação ou experimento comparativo agentic entregue. A CLI
atual tem sequência fixa; chamar um LLM para gerar texto não a torna agentic.

Para preparar a comparação, manter o fluxo determinístico como baseline e definir
mesmos incidentes, evidências, runbooks, modelo/limites e critérios de revisão.
Medir qualidade das evidências/citações, abstenções, respeito a P1, chamadas,
latência, recursos, rastreabilidade e necessidade de intervenção humana. Definir
antes quais decisões e ferramentas o agente poderá escolher; manter a proibição
de execução de ações. Não presumir que agentic será superior.

Esses são itens de planejamento da comparação, não experimentos realizados.

### Exercício de demanda de Negócios combinado — pendente

Registrar como atividade acordada e ainda não concluída. O enunciado específico
não foi localizado no repositório/documentos conferidos; não inventar requisitos
ou afirmar que o exercício já foi entregue.

Próxima definição necessária: recuperar/registrar com o usuário a demanda,
problema e resultado esperado. Como proposta de organização, não como reprodução
de um acordo anterior, registrar solicitante, usuário, valor esperado, escopo,
restrições, critérios de aceite, exemplos e dados necessários. Depois avaliar
quais partes a V1 atende, o que falta e se há razão para uma abordagem agentic.

## 8. Resultado desta revisão documental

Criado somente este documento. Conferidos código, contratos, testes selecionados,
casos JSON e registros versionados de integração/experimentos. Não houve execução
de testes, descoberta geral, evals, novas investigações/gerações ou alteração de
código, configuração, API, audit, índices ou política. Sem commit ou push.
