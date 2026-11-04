# Registro de decisões e dependências — POC simulada

Data: 2026-11-04. Referências: [cenário](scenarios/business-demand-simulated.md),
[proposta de quatro semanas](business-poc-four-week-proposal.md) e
[backlog da semana 1](business-poc-week1-backlog.md).

Este registro não declara disponibilidade de dados, acesso concedido, agendas
confirmadas ou resultados obtidos. Responsáveis são papéis do cenário; nomes e
autorizações ainda não foram informados. Onde falta um detentor de informação,
o gerente deve identificá-lo, sem presumir um participante adicional contratado.

## Convenção de prazo

`T0` é o início a acordar com Negócios; não há data de calendário confirmada.
`S1D2` significa o segundo dia útil da semana 1. As datas abaixo são datas
**necessárias propostas**, não compromissos já aceitos. A hipótese é cinco dias
úteis por semana, oito horas por dia de engenharia.

O encerramento-alvo é `S4D5`. Atraso, indisponibilidade de agenda ou suspensão de
sessão por risco não estendem esse prazo automaticamente. Renegociação deve
registrar responsável pela aprovação de Negócios, motivo, escopo, data anterior,
nova data e capacidade adicional. Sem aprovação explícita, manter o prazo e
entregar parecer de inviabilidade ou demonstração técnica reduzida com objetivo
explicitamente aceito. Demonstração com mocks não comprova valor operacional.

## Decisões e propostas de método

| ID | Decisão / proposta | Responsável pela confirmação ou execução | Data necessária | Situação e consequência |
|---|---|---|---|---|
| C01 | Engenharia 8 h/dia com Codex; planejar 40 h/semana em cinco dias úteis | Engenharia; gerente confirma calendário | Antes de T0 | Dedicação informada pelo usuário; calendário proposto. Ausências reduzem capacidade; IA não adiciona outra pessoa |
| C02 | Oito sessões finais: quatro manuais e quatro assistidas, duas de cada por analista, distribuídas em oito cenários distintos | Engenharia desenha; especialista valida equivalência; gerente aceita recorte | Desenho S1D3; congelamento S3D5 | Ajuste solicitado incorporado. Não são dezesseis sessões, nem amostra para inferência estatística |
| C03 | Revisar orientação antes de expor ao analista; incluir espera, revisão e correções no tempo e esforço assistidos | Especialista e gerente confirmam método; engenharia registra tempos | S1D3, antes do ensaio e da comparação assistida | Método proposto, ainda sem aceite dos participantes. Sem janela de revisão, não expor saída como orientação utilizável |
| C04 | Insuficiência e conflito limitados a checklists/casos definidos; encaminhar para revisão | Especialista define; engenharia limita a implementação; gerente aceita alcance | S1D3 | Ajuste solicitado incorporado; não há promessa de detecção semântica geral em quatro semanas |
| C05 | Reserva de 16 h em 160 h = 10%; retirar melhorias de apresentação, reduzir amostra e preservar controles/avaliação final | Engenharia acompanha; gerente aprova cortes | Desde S1D1; reavaliar ao prever esgotamento | Política de cortes incorporada; nenhum corte ou uso da reserva foi realizado |
| C06 | Sem extensão automática por atraso de dados; mudança exige renegociação com Negócios | Gerente conduz; autoridade de aceite de Negócios deve ser identificada | Antes de T0; decisão de contingência em S1D5 se houver bloqueio | Regra solicitada incorporada. Sem renegociação, continua valendo o encerramento em S4D5 |

## Dependências e decisões ainda abertas

| ID | Dependência / decisão | Responsável proposto | Data necessária | Situação atual | Consequência do atraso |
|---|---|---|---|---|---|
| D01 | Confirmar T0, calendário de cinco dias úteis e autoridade para aceite/renegociação | Gerente, com engenharia | Antes de T0; revisar em S1D1 | Não confirmado | Datas ficam relativas; não declarar compromisso real de entrega nem extensão automática |
| D02 | Identificar detentor e autorizar amostra, sanitização, uso somente leitura e armazenamento de artefatos | Gerente identifica o detentor; autorização cabe ao responsável ainda não informado | S1D2 | Não informado | Bloqueia inspeção da amostra e sessões com esses dados; não substituir autorização por suposição |
| D03 | Confirmar agendas do especialista e dos dois analistas dentro de 4 h/2 h/2 h semanais | Gerente articula com os papéis previstos | S1D1 para semana 1; reservar semana 4 até S3D3 | Pessoas previstas no cenário; agendas não confirmadas | Bloqueia revisões/baseline; reduzir recorte ou registrar inviabilidade, sem compensar com horas extras presumidas |
| D04 | Receber amostra sanitizada legível de incidentes, logs/métricas, procedimentos e históricos | Detentor a identificar por D02; engenharia confirma recebimento | S1D2 | Dados anunciados, não recebidos nesta entrega | Bloqueia S1/dados, preparação do recorte, S2/modelo e baseline representativa; escalar bloqueio em S1D2 |
| D05 | Validar status e versão dos documentos selecionados e quem pode classificá-los | Especialista; gerente confirma a autoridade pertinente | S1D3, dentro da hora de S1/dados; ampliar somente com recorte aceito | Não validado | Documentos não confirmados não fundamentam orientação; pode não haver base elegível para a POC |
| D06 | Aceitar rubrica, campos mínimos por caso, conflitos pré-identificados, revisão prévia e regra de interrupção | Especialista propõe; gerente confirma uso no piloto | S1D3 | Proposta a validar | Bloqueia ensaio assistido e julgamento comparável; não delegar aceite ao juiz semântico |
| D07 | Identificar o fluxo humano de P1 e como demonstrar o encaminhamento sem investigar | Gerente, com especialista | S1D3 | V1 interrompe P1; destino operacional não informado | Não alegar integração com o fluxo existente; controle P1 permanece obrigatório e o aceite fica pendente |
| D08 | Selecionar casos de baseline com checklist de próximas verificações, sem hipótese causal esperada | Especialista; engenharia prepara a ficha após D04/D05 | S1D3–S1D4, antes das sessões | Não selecionados | Baseline fica bloqueada; registrar falta de medição, não inventar referência ou ganho |
| D09 | Realizar baseline manual dos dois analistas, com tempos, falhas e feedback | Analistas previstos; engenharia observa | S1D4, após D02/D03/D08 | Não realizada | Metas de ganho não podem ser fundamentadas; decisão de semana 1 deve explicitar essa limitação |
| D10 | Discutir metas após baseline e decidir continuidade, recorte ou inviabilidade | Gerente, com especialista e engenharia | S1D5; compromisso final somente com registro de aceite | Não decidido | Não apresentar metas como acordadas nem manter silenciosamente o escopo original |
| D11 | Congelar casos finais, correspondência de complexidade, ordem, versão e parâmetros | Especialista valida; engenharia registra; gerente aceita redução se necessária | S3D5, antes de qualquer sessão final | Não iniciado | Sem congelamento, comparação não é apresentada como avaliação reservada; não ajustar versão no meio para melhorar resultados |
| D12 | Registrar uso da reserva, cortes e eventual renegociação de prazo/objetivo | Engenharia registra previsão/consumo; gerente obtém decisão de Negócios | Ao prever consumo acima da reserva; primeiro ponto de decisão em S1D5 | Nenhuma reserva consumida ou mudança aprovada | Preservar controles e avaliação final. Sem capacidade, entregar parecer; extensão só após renegociação explícita |

Ao chegar uma data necessária sem resposta, registrar **bloqueado** e a evidência
da pendência; não marcar a dependência como atendida. Na semana 1, engenharia pode
concluir um parecer sobre bloqueios sem concluir os itens que dependiam deles.

## Registro a completar nas decisões reais

Cada atualização futura deve registrar ID, data real, responsável identificado,
evidência recebida, decisão/limite autorizado, impacto em horas/amostra/prazo e
quem aprovou. Não retroagir aprovação, liberação de acesso ou conclusão de tarefa.

Este documento registra planejamento. Nenhuma solicitação externa foi enviada,
agenda marcada, amostra recebida ou atividade do backlog executada nesta entrega.
