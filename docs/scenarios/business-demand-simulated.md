# Cenário simulado de Negócios — investigação inicial de incidentes

Registrado em 2026-11-04 a partir do documento fornecido pelo usuário.

**Este é um cenário simulado para exercício de planejamento.** A expressão
“Entendimento aprovado por Negócios” pertence ao cenário; não comprova aprovação
real, contratação de pessoas, disponibilidade de dados, liberação de acesso ou
aceite de uma implantação. A proposta de atendimento está em
[plano de quatro semanas](../business-poc-four-week-proposal.md).

O conteúdo abaixo preserva o entendimento fornecido, normalizando apenas a
formatação da tabela de indicadores.

## Resumo executivo — entendimento aprovado no cenário

### 1. Problema e público prioritário

A equipe de Operações perde tempo buscando logs, consultando dashboards,
localizando procedimentos e identificando incidentes semelhantes. A qualidade e
a velocidade da investigação dependem da experiência do analista, gerando
investigações demoradas e escalonamentos prematuros.

O público prioritário são analistas iniciantes, buscando aproximar a qualidade
da investigação inicial à dos experientes. Para os mais experientes, o valor
está na agilidade e consolidação das informações.

### 2. O que pretende demonstrar em quatro semanas

Uma POC de IA para apoiar a investigação inicial de incidentes de checkout e
pagamentos, capaz de:

- Consolidar informações do incidente, evidências, procedimentos e históricos relevantes.
- Apresentar próximas verificações sugeridas, fundamentadas em fatos observados e fontes rastreáveis.
- Identificar informações insuficientes, evitando orientações sem suporte.
- Reconhecer incidentes P1 e direcioná-los ao fluxo humano existente.
- Impedir que documentos explicitamente descontinuados fundamentem orientações.

O objetivo das quatro semanas é demonstrar e avaliar a hipótese de valor,
fornecendo subsídios para decidir sobre novos investimentos, sem garantir ganhos
quantitativos antecipadamente.

### 3. Fora do escopo

- Diagnóstico automático e geração de hipóteses de causa.
- Execução automática de ações ou alterações em produção.
- Investigação assistida de incidentes P1, que seguirão o fluxo humano.
- Revisão completa, atualização e governança da documentação.
- Substituição dos especialistas, da decisão humana ou dos fluxos de aprovação.
- Garantia de cobertura de todos os cenários reais de incidentes.

### 4. Como pretende medir valor

Comparar investigações manuais e assistidas pela IA:

| Indicador | Objetivo |
|---|---|
| Tempo de investigação inicial | Reduzir o tempo para reunir evidências e definir próximas verificações |
| Cobertura das verificações | Avaliar se os pontos essenciais foram identificados |
| Qualidade do escalonamento | Verificar se evidências e perguntas estão adequadamente estruturadas |
| Confiabilidade das orientações | Identificar respostas incorretas, sem suporte ou potencialmente prejudiciais |

A linha de base será medida na primeira semana, quando serão discutidas as metas
quantitativas. Orientações potencialmente prejudiciais serão critério de
interrupção e revisão.

Não serão utilizados como indicadores principais o tempo total de resolução
nem a redução indiscriminada de escalonamentos.

### 5. Dependências e decisões pendentes

Recursos declarados pelo cenário:

- Responsável de engenharia pela implementação; o documento original não informava dedicação semanal.
- Especialista: 4 horas semanais.
- Dois analistas, um iniciante e um experiente: 2 horas semanais cada.
- Gerente de Operações: alinhamento semanal e demonstração final; duração não informada.

Complemento informado pelo usuário em 2026-11-04: desenvolvimento com apoio de IA
(Codex), com dedicação de engenharia de **8 horas por dia**. Para o planejamento,
adotam-se cinco dias úteis por semana: **40 h semanais e 160 h em quatro semanas**,
antes de descontar ausências. Codex é ferramenta de apoio, não uma pessoa adicional;
revisão, decisões, testes e validação fazem parte dessas horas.

Dados e condições declarados, ainda sujeitos a confirmação de disponibilidade:

- Aproximadamente 20 procedimentos e 40 incidentes históricos de checkout e pagamentos.
- Logs e métricas sanitizados, sem acesso de escrita à produção.
- Base selecionada e revisada com o especialista.
- Casos variados, incluindo ausência de procedimento aplicável, evidências
  incompletas e documentação conflitante ou descontinuada.

Decisões pendentes:

- Estabelecer a linha de base e definir as metas de ganho.
- Selecionar e validar os cenários de avaliação.
- Definir critérios mínimos de confiabilidade e classificação documental.
- Formalizar critérios de aceitação, especialmente para respostas insuficientes,
  orientações sem suporte e direcionamento de P1.

### Conclusão e direcionamento

Demonstrar se a IA consegue reduzir o esforço e melhorar a consistência da
investigação inicial, especialmente para analistas iniciantes, sem aumentar
o risco operacional.

A entrega será avaliada pela utilidade, confiabilidade, rastreabilidade e
segurança das orientações, mantendo decisão e execução sob responsabilidade humana.

Ao final das quatro semanas, avaliar as evidências coletadas para recomendar
continuidade, ajustes ou encerramento, sem compromisso antecipado de atingir
um ganho específico.
