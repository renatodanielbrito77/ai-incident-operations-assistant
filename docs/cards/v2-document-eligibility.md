# V2 — elegibilidade documental no executor local

Atualizado em 2026-11-06. **Estado: concluído tecnicamente no recorte isolado**,
com implementação, testes direcionados e validação funcional no Qdrant. Este card
local registra a entrega; não constitui integração da API, avaliação com analistas
ou comprovação de valor operacional.

## Objetivo e recorte

Reduzir o risco de usar procedimentos não aprovados como fundamento: somente
versões explicitamente ativas e consistentes com o catálogo podem chegar ao
contexto/pacote pelo componente controlado. Checkout; RB-V2-001 ativo e RB-V2-002
não confirmado, sem alterar classificações ou arquivos do lote.

## Critérios atendidos

| Critério | Evidência | Estado |
|---|---|---|
| Status/versão explícitos e regra única | Contratos classificados; ausências/divergências geram erro, não inferência pela idade | Atendido nos testes isolados |
| Inelegíveis fora antes do top 3 | Sem filtro: 3 não confirmados a 1,0; componente: 3 ativos a 0,8 | Atendido no Qdrant com vetores controlados |
| Orientação e Limites da mesma versão | RB-V2-001/1.0 no pacote; versão divergente rejeitada | Atendido na validação funcional |
| Reclassificação alcança todos os chunks/Limites | Transição técnica integral na coleção de teste | Atendido, sem mudar decisão humana do lote |
| Bloqueio persistente após interrupção | Processo encerrado após 1 de 4 chunks; novo processo bloqueou busca, Limites e pacote antes de ler backend | Atendido na validação funcional |
| Recuperação explícita | Reconciliação concluiu os 4 chunks e marcou ready; contexto antigo rejeitado, abstenção controlada sem ativos | Atendido no cenário de falha executado |
| Exclusividade | Outro processo não adquiriu lock enquanto ocupado | Atendido em teste isolado e funcional |
| Preservar V1 e coleções anteriores | Código inalterado; 3 coleções anteriores com pontos/payloads/vetores/configuração idênticos | Atendido no escopo conferido |
| Revisão EGM separada da execução | Etapas 5–8 executadas; etapa 7 convergiu; etapa 9 fora de feature_spec | Concluído como revisão documental, não prova funcional |

## Validação e artefatos

- [Especificação e decisão retrospectiva](../document-control-implementation.md).
- [Validação funcional e comandos executados](../document-control-functional-validation.md).
- [Parecer EGM final e estado das etapas](../../egm_feature_spec_final_report.md).
- 55 testes aprovados, código 0, mais 4 cenários assertivos de contexto; seleção
  direcionada em container sem rede, sem descoberta geral. São 30 novos e 25
  regressões V1. Sem mudança de código posterior que justifique repetir essa seleção.
- CLI funcional e roteiro de falha parcial: código geral 0; processo filho 73
  intencional. Somente duas coleções novas de validação, oito chunks cada.
- Materiais, estado persistente, roteiros temporários e evidências detalhadas ficam
  fora do Git em AI-Incident-POC-V2-Data/working. Nenhum desses arquivos é anexado
  a este card ou ao commit. A referência a eles não equivale a portabilidade dos dados.

## Limitações e pendências preservadas

- Componente/CLI isolados: API V1 continua sem integração nova. Nenhuma avaliação
  de endpoints ou participantes é presumida pela preservação de seus dados.
- Lock depende do mesmo estado canônico e acesso pelo componente. Não bloqueia
  clientes diretos do Qdrant ou outro diretório de estado; não há ACL no servidor.
- Classificação humana não é autenticada. State.json guarda catálogo vigente e
  predecessor global, não histórico acumulado ou audit completo. Audit da
  investigação é outro mecanismo, sem novos eventos de classificação.
- Recuperação comprovada para interrupção controlada de processo, não todos os
  modos de falha, queda de energia ou particionamento. Carga interrompida requer
  investigação; sem recuperação automática.
- Consultas podem ficar indisponíveis durante reclassificação. Reavaliar desenho
  diante de múltiplos escritores independentes, réplicas, volume/contenção ou
  necessidade de leitura durante transições.
- Vetores controlados não avaliam embeddings ou qualidade semântica; nenhum LLM,
  novo modelo, ação operacional ou ganho percentual foi produzido.
- Nit editorial CRIT-03 permanece registrado: “encerrar o achado” sem antecedente.
  Não bloqueia convergência e não foi corrigido como parte do fechamento.
- Contextos de planejamento citados pelos revisores refletem a versão local da
  simulação. Suas demais atualizações pendentes não integram este commit restrito;
  referências históricas de linhas não devem ser tratadas como snapshot publicado
  de todo o planejamento.

## Esforço e próximos passos

Esforço humano contínuo não medido; estimativa anterior de 30 h não foi registrada
como realizada. Aprovação da decisão arquitetural é retrospectiva; custos das
alternativas são qualitativos, não medição.

Qualquer integração da API, evolução de segurança/rastreabilidade, avaliação
semântica ou com participantes precisa de escopo/autorização próprios. Coleções de
validação permanecem preservadas; não excluir ou reutilizar seus nomes
silenciosamente para repetir testes.
