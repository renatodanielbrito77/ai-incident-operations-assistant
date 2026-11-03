# Revisão por afirmação: candidata de INC-001 com teto de 512 tokens

Data da execução: 2026-11-03. Revisão qualitativa assistida para avaliação humana,
sem nova geração, avaliador semântico automático ou alteração da candidata.
Complementa o [relatório consolidado](ollama_candidate_experiments_report.md),
experimento E3, que passou nas verificações estruturais.

## Fonte e critérios

Fonte: candidata e pacote preservados em
`/private/tmp/ollama-output512.StxEYv/run/`, conferidos nesta revisão.
O `audit_event_id` de origem é `afc36a70-04a9-4039-9631-d8820c2f115c`.

- **Fato atual:** precisa ser demonstrado pelos dados do incidente. Um runbook
  pode descrever o mesmo sintoma, mas não comprova sua ocorrência neste caso.
- **Fato histórico:** deve permanecer identificado como passado. Uma resolução
  anterior não se converte automaticamente em sugestão para o incidente atual.
- **Sugestão:** precisa preservar as condições e limitações da orientação citada.
- **Sustentado:** o contexto demonstra a afirmação no alcance em que é apresentada.
- **Impreciso:** há suporte parcial, mas a formulação generaliza, mistura escopos
  ou omite condições relevantes.
- **Não sustentado:** não há suporte no contexto para o uso proposto da informação.
  Isso não significa que a afirmação foi demonstrada falsa.

A candidata citou globalmente apenas `RB-001-02-01`, `RB-001-03-02` e
`RB-001-04-02`. O contrato não relaciona IDs a frases individuais: as associações
na tabela são feitas pela revisão, sem atribuir ao modelo uma rastreabilidade
que ele não forneceu. Logs, métricas e históricos estão disponíveis como dados,
mas não são referências documentais em `cited_chunk_ids`.

`RB-001-05` está disponível em `document_limits`, mas **não foi citado pela
candidata**. Ter suporte disponível não equivale a ter citado esse suporte.

## Tabela revisada

As aspas contêm fragmentos literais da candidata. As conjunções e complementos
mantidos em algumas linhas dependem gramaticalmente da frase anterior; a divisão
serve somente à revisão, sem reescrever o texto original. Não há linha que
reavalie a sugestão composta de pagamentos e pool de conexões.

| Afirmação ou sugestão exata | Origem e natureza | Evidência disponível no contexto | Evidência citada pela candidata | Classificação | Justificativa curta |
|---|---|---|---|---|---|
| “O incidente ocorreu no aplicativo checkout” | Evidência atual — fato atual | `incident.application="checkout"`, incidente `INC-001`. | `RB-001-02-01` menciona checkout como aplicação do runbook; não comprova o incidente atual. | `sustentado` | A aplicação é demonstrada pelos dados do incidente. |
| “com status de degradação” | Evidência atual — fato atual | `monitoring.status="degraded"`. | `RB-001-02-01`: monitoring de checkout com status `degraded`, como sinal de relevância do runbook. | `sustentado` | O estado atual vem do monitoring, não da descrição documental do sintoma. |
| “e taxa de erros de 12.5%.” | Evidência atual — fato atual | `monitoring.error_rate_percent=12.5`. | `RB-001-02-01`: “Taxa de erros acima de 5%”; não informa o valor atual de 12,5%. | `sustentado` | O valor exato é demonstrado pela métrica atual. |
| “Houve logs de erro” | Evidência atual — fato atual | Entrada `ERROR`, às `2026-10-05T12:00:00Z`, com `Timeout while connecting to payment service`. | `RB-001-02-01` descreve esse nível e essa mensagem como sintoma; não comprova que o registro ocorreu agora. | `sustentado` | A ocorrência é demonstrada pela entrada de log fornecida. |
| “e aviso de latência elevada.” | Evidência atual — fato atual | Entrada `WARN`, às `2026-10-05T12:00:05Z`, com `Payment request exceeded latency threshold`. | `RB-001-02-01` descreve esse aviso como sintoma. | `sustentado` | A mensagem atual informa excesso do limiar de latência. |
| “Os timeouts foram registrados em 2026-10-05T12:00:00Z” | Evidência atual — fato atual | Uma entrada explícita de timeout no horário indicado. | `RB-001-02-01` descreve a mensagem de timeout, sem horários de ocorrência. | `impreciso` | O horário tem suporte para um timeout; o plural não é demonstrado pelo recorte atual. |
| “e 2026-10-05T12:00:05Z.” | Evidência atual — continuação da afirmação de timeout | Nesse horário, o registro é `Payment request exceeded latency threshold`, nível `WARN`. | `RB-001-02-01` distingue o aviso de latência da mensagem de timeout. | `impreciso` | O segundo registro não declara timeout; não deve ser contado como outra ocorrência explícita. |
| “O monitoring indicou latência p95 de 1800 ms.” | Evidência atual — fato atual | `monitoring.latency_p95_ms=1800.0`. | `RB-001-02-01`: “Latência p95 acima de 1.000 ms”; não fornece o valor atual. | `sustentado` | Métrica e valor são demonstrados pelo monitoring. |
| “Os dados do histórico mostram que há similaridades em problemas de timeout e latência elevada” | Histórico — comparação identificada como histórica | `HIST-001` contém sintomas de timeout e p95 acima de 1000 ms; os dados atuais também mostram timeout e p95 de 1800 ms. | Nenhum histórico está em `cited_chunk_ids`. `RB-001-02-01` descreve sintomas compatíveis, mas não comprova o episódio passado. | `sustentado` | A origem histórica está indicada. A similaridade não comprova mesma causa nem recorrência no incidente atual. |
| “mas não foi comprovado que a configuração seja a única causa.” | Histórico — ressalva sobre resultado passado | `HIST-001.observed_result`: “Não foi comprovado que a configuração era a única causa.” | Nenhum dos três chunks citados comprova essa avaliação histórica. | `impreciso` | A ressalva tem suporte no passado, mas deve ser vinculada explicitamente a HIST-001, sem transferência ao incidente atual. |
| “Solicitar verificação do status do serviço de pagamentos” | Runbook — sugestão | Há degradação e um log explícito de timeout. `RB-001-04-02` orienta consultar monitoring e logs de pagamentos quando houver **timeouts recorrentes acompanhados de degradação**; se esses dados não estiverem disponíveis, informar a limitação e solicitar verificação. Monitoring/logs de pagamentos não foram fornecidos no pacote. | `RB-001-04-02` está citado e contém essa orientação condicional. `RB-001-03-02`, também citado, impede presumir indisponibilidade apenas pelo timeout. | `impreciso` | A recorrência não está demonstrada por um único log explícito de timeout. A sugestão omite essa condição, a consulta aos logs e a limitação dos dados não fornecidos. |
| “e da configuração do pool de conexões.” | Histórico — sugestão ligada ao verbo “Solicitar verificação” | `HIST-001.resolution`: a equipe reverteu uma alteração recente no pool de conexões. Isso demonstra uma ação passada, não uma orientação para o caso atual. | Nenhum dos três chunks citados orienta verificar o pool de conexões. | `não sustentado` | A resolução histórica, sozinha, não fundamenta a sugestão atual. Não se conclui que verificar o pool seja proibido ou inútil. |
| “Não há dados suficientes para concluir a causa raiz.” | Evidência atual — limitação da conclusão | O contexto contém sintomas, métricas e exemplos históricos, mas não demonstra um mecanismo causal ou causa raiz para INC-001. `RB-001-05`, disponível mas não citado, reforça que timeout sozinho não permite concluir causa raiz. | `RB-001-03-02` foi citado e reforça a cautela contra presumir indisponibilidade por timeout. **`RB-001-05` não foi citado.** | `sustentado` | O alcance da afirmação é a causa raiz não demonstrada pelo contexto. A regra documental reforça a cautela; não comprova, sozinha, insuficiência dos dados. |

## Síntese e limitações

A candidata contém fatos atuais demonstrados, mas generaliza um aviso de latência
como timeout, não mantém inequívoco o alcance de uma conclusão histórica e sugere
verificação do pool com base insuficiente nas orientações disponíveis. A sugestão
de investigar pagamentos precisa preservar a condição de recorrência, que não
está comprovada no recorte de logs atual. A ausência de comprovação de recorrência
também não demonstra que os timeouts não se repetiram fora desse recorte.

A revisão distingue presença de informação, uso adequado e citação. Referência
presente no contexto não sustenta automaticamente toda a candidata; suporte
encontrado pela revisão em um chunk não citado não corrige retroativamente as
referências fornecidas pelo modelo.

Esta tabela cobre apenas uma candidata e o contexto já fornecido. Não houve
busca adicional, alteração de código, mudança de classificação automática ou
geração de nova resposta. `semantic_support_status` permanece `not_evaluated`.
