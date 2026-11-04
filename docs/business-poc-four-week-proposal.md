# Proposta de quatro semanas para o cenário simulado de Negócios

Data: 2026-11-04. **Proposta para avaliação, com backlog proposto somente da semana 1.**
Fonte: [cenário simulado fornecido pelo usuário](scenarios/business-demand-simulated.md).
Não representa aceite real de Negócios nem confirma dados ou acessos. A dedicação
de engenharia foi esclarecida pelo usuário: 8 h/dia com apoio do Codex. Sem
implementação, testes, chamadas a serviços ou novas gerações
nesta elaboração.

Complementos: [registro de decisões e dependências](business-poc-decisions-dependencies.md)
e [backlog da semana 1](business-poc-week1-backlog.md). São documentos de
planejamento, sem tarefas executadas ou aprovações presumidas.

## 1. Direção proposta

Reaproveitar a [V1 local](v1-review.md) como infraestrutura da investigação,
mantendo a sequência determinística e a geração de candidatas sujeita a revisão
humana. A hipótese a avaliar é o auxílio à investigação inicial, sobretudo do
iniciante; não é diagnóstico, geração de hipóteses causais ou execução de ações.

A primeira semana deve decidir se há condições para executar as demais. Se os
dados ou o tempo das pessoas não estiverem disponíveis, não substituir a avaliação
de valor por uma demonstração com mocks e apresentá-la como equivalente.

Uma interface web, agentic, busca semântica de históricos, novo juiz semântico e
infraestrutura de produção não entram na primeira fatia. São escolhas posteriores
se houver necessidade demonstrada. A comparação manual versus assistido pedida
por Negócios é diferente da comparação determinístico versus agentic pendente
de V2; esta não é dependência para avaliar a hipótese em quatro semanas.

## 2. Inspeção da V1: reaproveitar, mudar e esclarecer

| Capacidade | Reaproveitar | Mudança necessária ao novo cenário | Ainda desconhecido |
|---|---|---|---|
| Coleta de incidente, logs e métricas | Orquestração, contratos, respostas e tratamento de falhas em [main.py](../ai-app/main.py) | Adaptar uma amostra sanitizada e somente leitura; delimitar a evidência de checkout versus pagamentos e a janela do incidente | Formatos, completude, acesso, autorização e identificadores dos dados reais |
| P1 | Retorno antecipado, audit e inelegibilidade sem LLM | Confirmar campos de prioridade e tornar o direcionamento ao fluxo humano existente claro no relatório | Quem recebe, por qual processo e qual evidência comprova o direcionamento; hoje não existe notificação efetiva |
| Suficiência das evidências | [has_log_message](../ai-app/evidence_rules.py), solicitação de dados, abstenções e erros distintos | Detectar somente ausências definidas em checklists dos casos selecionados e encaminhar para revisão; não interpretar log não vazio como suficiência nem prometer reconhecimento semântico geral | Quais campos/regras limitados o especialista valida e como tratar evidências fora do período |
| Histórico | Filtro por aplicação, correspondência exata e distinção recuperado/correspondente | Usar somente históricos selecionados, preservando origem e caráter passado; não promover resolução anterior a próxima ação | Se correspondência literal e filtro são úteis no material disponível; quais exemplos realmente ajudam os analistas |
| Recuperação documental | Qdrant, IDs, fontes, Limites e avaliadores existentes | Preparar ingestão de mais de um documento; registrar versão e classificação do subconjunto selecionado | Estado e qualidade dos procedimentos, fontes conflitantes e disponibilidade de critérios para classificá-los |
| Documentos descontinuados | Infraestrutura de filtros e referências | Controle explícito de elegibilidade documental na busca, Limites, contexto e citações; teste adversarial com documento descontinuado muito semelhante | Quem valida o status e o comportamento acordado para status desconhecido ou conflito |
| Geração e relatório | [Pacote](../ai-app/llm_input_package.py), [CLI](../experiments/investigate_and_report.py), resposta bruta e [relatório](../ai-app/recommendation_report.py) | Separar fatos e verificações; preservar condições; não gerar hipóteses de causa; identificar lacunas e informações efetivamente citadas | Utilidade e confiabilidade com casos representativos e latência no ambiente escolhido |
| Validação e decisão humana | Contratos, regras de referências/ação e [revisões](../experiments/investigate_and_report_validation.md) | Rubrica do especialista, registro de avaliação, erros e regra de interrupção | Níveis aceitáveis de imprecisão, insuficiência e risco; os validadores atuais não aferem esses níveis |
| Rastreabilidade | `audit_event_id`, etapas, arquivos de parâmetros/entrada/saída | Manifesto do conjunto e da execução, versões e retenção suficiente para a demonstração | Política de retenção e autorização para armazenar dados sanitizados; geração ainda não é evento do audit da API |
| Avaliação de valor | Evals e dados mockados como regressão técnica | Baseline manual, sessões observadas e comparação assistida com analistas | Tempo atual, cobertura e qualidade do escalonamento; não existem resultados de valor de Negócios na V1 |

Constatações críticas do código: [search_qdrant.py](../ai-app/search_qdrant.py)
não filtra estado de ciclo de vida; [RunbookChunk](../ai-app/investigation_models.py)
não declara esse estado. A consulta de Limites filtra somente documento/seção.
[read_runbook.py](../ai-app/read_runbook.py) prepara o RB-001 específico. A
[decisão de contexto](../ai-app/context_rules.py) verifica presença documental e
Limites, não suficiência semântica das evidências ou classificação documental.
Não se pode afirmar que a V1 já atende à proteção de documentos descontinuados.

O [juiz semântico experimental](../experiments/claim_judge_experiment_report.md)
teve duas saídas válidas, uma concordância e uma divergência, além de uma saída
rejeitada. Não é um controle de confiabilidade demonstrado e não será usado para
aprovar orientações ou substituir o especialista.

## 3. Fatia proposta e condições de capacidade

Há uma pessoa de engenharia com apoio do Codex, com dedicação informada de
**8 h/dia**. Assumindo cinco dias úteis, são **40 h/semana e 160 h em quatro
semanas**, antes de descontar ausências. Esse é o orçamento total: inclui análise,
interação com a IA, revisão do código gerado, testes, documentação, coordenação e
reserva para problemas. Não corresponde a 160 horas líquidas de implementação.
Codex não adiciona outra pessoa nem garante multiplicador de produtividade.
Planejar uma frente de implementação por vez, com revisão do especialista.

Capacidade declarada em quatro semanas: **16 h de especialista, 8 h do iniciante
e 8 h do experiente**. Reuniões, preparação, testes e demonstração consomem essas
mesmas horas. O gerente tem alinhamentos e demonstração previstos, sem duração
declarada; propõem-se alinhamentos de até 30 min e demonstração de até 30 min,
sujeitos à confirmação.

Como proposta de redução de escopo, selecionar inicialmente **até quatro
procedimentos, até oito históricos e oito cenários curtos não-P1 para comparação
final**, além de testes separados de proteção de P1 e casos distintos de
desenvolvimento/baseline quando houver material. São
limites de trabalho propostos, não dados confirmados ou cobertura representativa
do total de 20/40. A seleção e qualquer redução precisam de aceite no fim da
semana 1. Não prometer revisão e ingestão integral de 20 procedimentos e 40
históricos dentro das quatro horas semanais do especialista.

Os oito cenários finais propostos terão uma sessão cada: **oito sessões finais,
quatro manuais e quatro assistidas**, com duas de cada modalidade por analista.
Não são oito cenários executados nas duas modalidades, o que exigiria dezesseis
sessões. A distribuição nominal está na seção 7; a baseline da semana 1 é separada.

Cobrir, na seleção aceita: não-P1 com suporte, mensagem de log ausente, evidências
presentes mas insuficientes, ausência de procedimento aplicável, documento
descontinuado, conflito documental previamente identificado e P1. A insuficiência
é limitada a ausências previamente definidas pelo especialista para esses casos;
conflitos são casos cadastrados/identificados no subconjunto, encaminhados para
revisão. Não se promete detecção geral de conflitos ou suficiência semântica em
quatro semanas. Casos técnicos de proteção podem
ser fixtures construídas e identificadas como tais; não contam automaticamente
como casos reais nem como medição de valor. Se a amostra não cobrir essas famílias,
registrar a lacuna e reavaliar a demonstração, em vez de declarar cobertura.

## 4. Entregas semanais e aceite proposto

As semanas são relativas ao início acordado, sem datas de calendário presumidas.
As entregas e seus critérios são propostas a validar. Somente a semana 1 tem
backlog estimado nesta revisão. O prazo-alvo é de quatro semanas desde o início
acordado: atraso de dados não o estende automaticamente. Suspensão da contagem,
nova data ou alteração de escopo dependem de renegociação explícita com Negócios,
registrada pelo gerente. Sem renegociação, o encerramento permanece no prazo
original e pode entregar um parecer de inviabilidade ou demonstração técnica com
objetivo reduzido explicitamente aceito, sem alegar avaliação de valor não realizada.

| Semana | Entrega verificável | Critérios de aceite propostos | Evidência e decisão ao fim da semana |
|---|---|---|---|
| 1 — viabilidade e baseline | Recorte e dados autorizados; catálogo documental inicial; rubrica; baseline manual; metas discutidas | Amostra recebida ou bloqueio registrado; origem, sanitização e uso permitidos confirmados; especialista identifica documentos ativos, descontinuados e status não confirmado; cada analista executa sessões manuais registradas; critérios de risco/P1/insuficiência e metas são discutidos e registrados; escopo estimado dentro das 40 h/semana de engenharia | Manifesto e acesso à amostra, folha de baseline, checklist de referência, decisões pendentes e resultados dos dois spikes. Gerente/especialista autorizam continuar, reduzir com escopo explícito, adiar ou encerrar. Sem dados/baseline não declarar início de avaliação assistida comparável |
| 2 — contexto elegível e documentação controlada | Fatia de coleta sanitizada e recuperação rastreável com bloqueio documental | Nos casos selecionados, P1 não consulta contexto adicional nem chama LLM e apresenta encaminhamento acordado; documentos descontinuados não entram na busca, nos Limites ou no pacote; status desconhecido não fundamenta orientação até classificação; ausência de procedimento, erro operacional e ausências previstas em checklist permanecem distintos; conflitos previamente identificados são sinalizados e encaminhados ao especialista | Testes isolados e integrações controladas do recorte, IDs/versões/status e exemplos negativos. Não se demonstra reconhecimento geral de conflitos ou suficiência. Falha de controle essencial bloqueia a avaliação assistida |
| 3 — orientações revisáveis e protocolo congelado | Relatório útil com fatos, verificações, condições e lacunas; ensaio; casos finais reservados | Uma geração por caso no protocolo; saída inválida/limite registra erro e para, sem reparar; especialista revisa antes da exposição ao analista e registra tempo, correções e bloqueios; verificação não realizada não é narrada como fato; histórico não vira ação atual; aplicar somente checklists e conflitos definidos; congelar versão, conjunto final, prompts/parâmetros e metas antes da comparação final | Relatórios originais e revisões humanas separados; tempos de espera/revisão incluídos no processo assistido; regras de insuficiência limitadas ao catálogo de casos. Orientação potencialmente prejudicial interrompe a sessão e exige revisão, sem nova tentativa para apagar o resultado |
| 4 — comparação e decisão | Sessões manual/assistida, demonstração e recomendação de investimento | Comparar condições com mesmo início/fim e recursos; incluir falhas, abstenções e interrupções; especialista aplica a rubrica registrada; apresentar resultados por analista e cenário, sem taxa geral enganosa; revisar proteção de P1/documentos e rastreabilidade; decidir continuidade, ajustes ou encerramento com justificativa | Dossiê final com tempos, cobertura, escalonamentos, revisão de confiabilidade, artefatos, desvios e limitações. Não requer ganho antecipado específico para concluir honestamente o experimento |

Diretriz de insuficiência a formalizar na semana 1: para os casos/checklists
definidos, identificar qual informação necessária à próxima verificação não foi
fornecida; pedir esse dado ou encaminhar/abster a orientação que dependa dele,
sem concluir que ele não existe. O enquadramento no catálogo de casos depende
da triagem humana; fora dele não se declara suficiência semântica e encaminha-se
para revisão, sem prometer identificação automática de todo caso desconhecido. A ausência de
causa raiz conhecida não é, sozinha, um erro da POC: diagnosticar está fora do escopo.

A classificação mínima proposta para o subconjunto é ativo, explicitamente
descontinuado e não confirmado. O controle é uma elegibilidade determinada pelo
catálogo validado, não uma inferência do LLM nem a governança completa do acervo.
Mudar uma classificação deve deixar rastro e invalidar uso de versões/pontos
obsoletos; excluir só o nome na resposta final não basta. Conflitos previamente
identificados exigem limitação explícita e revisão humana; conflitos não previstos
não têm detecção garantida e não serão resolvidos automaticamente.

## 5. Uso das horas dos participantes

Distribuição proposta do orçamento de engenharia. A semana 1 está detalhada no
[backlog](business-poc-week1-backlog.md); as demais seguem como reservas macro:

| Semana | Uso das 40 h de engenharia com apoio do Codex |
|---|---|
| 1 | 22 h de tarefas iniciáveis com a V1 e a informação disponível; 14 h de tarefas condicionadas a dados/agendas; 4 h reserva. Total estimado do backlog: 40 h, sem presumir desbloqueio |
| 2 | 24 h contexto e controles documentais; 8 h testes e revisão; 4 h coordenação/documentação; 4 h reserva |
| 3 | 20 h geração e apresentação; 12 h testes, revisão e avaliação técnica; 4 h coordenação/documentação; 4 h reserva |
| 4 | 12 h preparação, suporte e coleta das sessões; 8 h análise dos resultados; 8 h conferência de rastreabilidade/artefatos; 8 h relatório e decisão; 4 h reserva |

Essas reservas incluem o trabalho com IA e sua conferência. Não usar a semana 4
para ajustar a versão durante a comparação congelada. Maior capacidade de
engenharia não aumenta as horas de validação dos demais participantes; o recorte
inicial permanece até reavaliação com o especialista e disponibilidade dos dados.

Orçamento proposto, já incluindo reuniões e revisões; distribuição exata depende
da confirmação das agendas e da complexidade da amostra.

| Semana | Especialista: no máximo 4 h | Cada analista: no máximo 2 h | Engenharia e gerente |
|---|---|---|---|
| 1 | 0,5 h alinhamento; 1 h S1/dados/status; 0,5 h S2; 0,5 h aprovação da rubrica; 1,5 h referências dos casos/baseline | 0,5 h orientação; 1 h baseline manual de dois casos curtos; 0,5 h feedback | Engenharia conduz os spikes e registra decisões antes de implementar. Gerente decide escopo, metas e continuidade no alinhamento |
| 2 | 0,5 h alinhamento; 1,5 h classificação e controles documentais; 1 h referências para casos; 1 h revisão da fatia | 0,5 h alinhamento; 1 h revisão de relatórios/fluxo de trabalho; 0,5 h feedback | Engenharia entrega primeiro o contexto e os controles, sem uma segunda frente de interface ou agente |
| 3 | 0,5 h alinhamento; 2 h revisão das orientações de desenvolvimento; 1,5 h rubrica e reserva dos casos finais | 0,5 h alinhamento; 1 h ensaio com casos de desenvolvimento; 0,5 h feedback | Engenharia corrige problemas prioritários e congela versão. Não usar casos finais para ajustar prompts |
| 4 | 0,5 h alinhamento; 1 h revisão prévia das quatro saídas assistidas; 1 h avaliação posterior dos oito relatórios dos analistas; 0,5 h demonstração; 1 h consolidação/decisão | 80 min de quatro sessões de até 20 min, incluindo esperas/revisão prévia nas assistidas; 10 min feedback; 30 min demonstração | Engenharia opera e coleta registros. Gerente participa da demonstração e decide a recomendação final |

Se uma atividade exceder essas reservas, reduzir o recorte com decisão explícita
ou renegociar o prazo. Não transferir implicitamente revisão para fora das horas
disponíveis. Se a revisão prévia das quatro orientações assistidas e a avaliação
posterior dos oito relatórios não couberem, reduzir a amostra e a força das
conclusões; não substituir a revisão pelo juiz experimental.

### Reserva, cortes e prazo

São **4 h de reserva por semana, 16 h em 160 h: 10% da capacidade de engenharia**,
não capacidade adicional. Consumo, motivo e saldo devem ser registrados; os
spikes já estimados não são cobrados novamente na reserva.

Ao prever esgotamento da reserva, aplicar os cortes nesta ordem, com o gerente:

1. Retirar melhorias não essenciais de apresentação/usabilidade, mantendo as
   evidências, fontes, alertas e o relatório mínimo legível.
2. Reduzir volume de documentos/históricos e depois o tamanho da amostra final,
   reequilibrando manual/assistido por analista quando possível. Uma redução para
   quatro sessões finais, uma manual e uma assistida por pessoa, torna a comparação
   ainda mais limitada e deve ser declarada. Não cortar só casos difíceis para
   produzir resultado favorável nem usar casos de desenvolvimento como finais.
3. Se ainda não couber, pedir decisão sobre objetivo reduzido/parecer de
   inviabilidade ou renegociar formalmente. Não estender o prazo por conta própria.

Preservar os controles essenciais: P1 sem assistência, ausência de escrita/ações
em produção, bloqueio de documentos descontinuados, revisão humana prévia e
interrupção por orientação potencialmente prejudicial, rastreabilidade e
registro honesto de erros/abstenções. Preservar também a avaliação final e sua
recomendação, ainda que seja necessário concluir que não houve condições para
avaliar valor. Se esses mínimos não couberem, não apresentar piloto operacional.

## 6. Spikes somente para riscos que podem inviabilizar a POC

| Spike de viabilidade | Pergunta fatal | Limite de investigação proposto, dentro da semana 1 | Saída e consequência |
|---|---|---|---|
| Dados utilizáveis e classificáveis | É possível obter em tempo uma amostra autorizada/sanitizada com ligação entre incidente, logs/métricas, documentos e status documental confiável? | Até 2 h de engenharia e 1 h do especialista, usando uma amostra já liberada; solicitações de acesso são dependências, não pesquisa indefinida | Inventário verificado, campos faltantes e status conhecido/desconhecido. Sem liberação ou classificação, registrar bloqueio e solicitar decisão ao gerente. Alteração da data exige renegociação com Negócios; sem isso, entregar parecer ou objetivo reduzido aceito no prazo original |
| Utilidade e viabilidade do modelo local | Com dados representativos, a abordagem produz orientação revisável sem risco inaceitável e dentro do tempo/recursos úteis para a investigação inicial? | Até 2 h de engenharia e 0,5 h do especialista, dentro de suas horas semanais; poucos casos de desenvolvimento, parâmetros explícitos, sem busca aberta de modelos/prompts | Registro de latência, contexto, falhas e revisão de conteúdo. Orientação potencialmente prejudicial interrompe o ensaio. Sem perspectiva de utilidade dentro do orçamento, recomendar ajuste de escopo, adiamento negociado ou encerramento, sem trocar silenciosamente de arquitetura |

Os limites não são estimativas totais da implementação. Sem amostra liberada,
o segundo spike fica bloqueado; dados fictícios só demonstram funcionamento
técnico, não resolvem a incerteza de valor. Resultado positivo do spike não
certifica confiabilidade — apenas justifica continuar com avaliação controlada.

Não criar spikes para o filtro de documentos, novos estados ou manifesto: são
trabalhos de implementação após decisão. Nem para agentic, Kubernetes, interface
completa ou comparação ampla de modelos: não respondem a uma incerteza fatal
necessária a esta fatia de quatro semanas.

## 7. Medição proposta e condições da comparação

| Indicador | Definição operacional proposta | Evidência necessária |
|---|---|---|
| Tempo de investigação inicial | Do recebimento do caso até entregar evidências reunidas, próximas verificações e decisão de encaminhamento; incluir geração, fila/espera, revisão prévia do especialista, eventuais correções e trabalho do analista | Tempo decorrido completo e esforço humano separado por papel, com falhas/interrupções/limites. Não somar horas simultâneas como tempo decorrido nem excluir revisão para aparentar ganho |
| Cobertura das verificações | Checklist essencial por caso, preparado pelo especialista, comparado ao que o analista identificou | Checklist por cenário, itens atendidos/omitidos/inaplicáveis e justificativas; referência não contém hipótese de causa a ser adivinhada |
| Qualidade do escalonamento | Clareza de evidências, período, informações ausentes, perguntas e direcionamento ao fluxo humano | Relatório manual/assistido avaliado pela mesma rubrica. Não penalizar um escalonamento necessário nem medir apenas sua quantidade |
| Confiabilidade das orientações | Afirmações suportadas, imprecisas, sem suporte e potencialmente prejudiciais, classificadas pelo especialista com regra de insuficiência/abstenção | Texto original, evidências disponíveis versus citadas, condições omitidas, severidade, decisão de interrupção e revisão |

Semana 1: baseline exploratório manual, dois casos curtos por analista, dentro
da hora reservada. Registrar experiência e ferramentas utilizadas, interrompendo
ao atingir o limite da sessão sem registrar conclusão artificial. Discutir metas
após observação; metas, limites de sessão e critérios precisam estar registrados
antes de congelar a avaliação final.

Semana 4: propor dois pares de cenários de complexidade semelhante por analista,
com um manual e um assistido em cada par. A distribuição final é:

| Analista | Sessões manuais | Sessões assistidas | Total |
|---|---:|---:|---:|
| Iniciante | 2 | 2 | 4 |
| Experiente | 2 | 2 | 4 |
| Total | 4 | 4 | 8 |

Os oito cenários finais são distribuídos nessas oito sessões, uma sessão por
cenário. São quatro pares de complexidade semelhante, não o mesmo caso repetido
nas duas condições. A equivalência é avaliada pelo especialista, com possível
viés residual. Alternar a ordem, sem repetir caso para a mesma pessoa, usar casos
reservados e permitir os mesmos materiais de referência. As quatro sessões
manuais exploratórias da semana 1 não entram na contagem dessas oito finais.
O teto de 20 min por sessão é uma proposta operacional para caber nas duas horas,
não meta de ganho. Caso incompleto no teto não recebe tempo de sucesso de 20 min.

### Revisão antes e avaliação depois

Propõe-se que o especialista revise cada orientação **antes de sua exposição ao
analista**. A sessão começa antes da geração; espera, revisão, decisão de bloqueio
e eventuais correções manuais integram o tempo do processo assistido e o esforço
do especialista. Reservam-se até 15 min de especialista por saída assistida, no
total de 1 h; isso não garante que a revisão termine nesse prazo.

Conservar a saída original e qualquer versão humana separadamente, com motivo,
tempo e autor por papel. Correção humana de conteúdo não é reparação automática
de JSON nem transforma saída de modelo inválida em geração bem-sucedida. Se a
saída for potencialmente prejudicial, interromper e registrar; não corrigir e
continuar silenciosamente para obter sucesso na mesma observação.

Depois, aplicar a rubrica aos relatórios entregues pelos analistas; não confundir
essa avaliação posterior com a revisão prévia de segurança. O mesmo especialista
pode reconhecer a condição por ter revisado antes, portanto não se promete
cegamento independente. Registrar familiaridade e esse viés. A medição avalia
**analista + ferramenta + revisão do especialista**, não o LLM isolado.

O teto de 20 min inclui a revisão prévia e eventuais filas. Se faltar tempo para
o analista terminar, registrar sessão incompleta; não retirar a revisão da conta
nem usar relatório previamente corrigido fora da medição. A amostra de dois
analistas e oito sessões é exploratória, sem inferência estatística ou ganho geral.

P1 participa dos testes de proteção/encaminhamento, não de investigação assistida.
Em caso de orientação potencialmente prejudicial, suspender a sessão/versão,
preservar a ocorrência e revisar antes de eventual retomada aprovada. Não
continuar gerando até obter saída favorável nem excluir a ocorrência das métricas.

## 8. Dossiê necessário à demonstração final

1. Escopo aceito e decisões da semana 1, incluindo a alocação das 40 h/semana de engenharia,
   dados recebidos versus anunciados, metas acordadas e critérios de risco.
2. Manifesto do subconjunto autorizado: fontes, sanitização, IDs/versões, status
   documental, cenários construídos versus dados recebidos e responsáveis pela revisão.
3. Protocolo e checklist por caso: baseline, divisão desenvolvimento/avaliação,
   limites de sessão, ordem e perfis dos dois analistas.
4. Evidências técnicas por caminho: P1 sem LLM; ausências definidas em checklist e
   ausência de procedimento; conflito previamente identificado; descontinuado
   excluído mesmo com similaridade alta;
   erros operacionais sem orientação fabricada; distinção de abstenção e erro.
5. Para cada execução assistida: entrada sanitizada, fontes/citações, versão,
   modelo/parâmetros, saída bruta, término, resultado e correlação de audit,
   preservados em local acordado. Mesma rastreabilidade para erros e abstenções.
6. Quatro sessões manuais e quatro assistidas, divididas igualmente por analista,
   ou redução aprovada e declarada: tempos completos incluindo revisão prévia,
   esforço de cada papel, cobertura, escalonamento, falhas e interrupções, sem apresentar validação
   estrutural como aprovação semântica.
7. Demonstração de uma orientação útil e dos principais encerramentos seguros,
   identificando se são registros gravados ou execução ao vivo autorizada.
8. Recomendação final de continuar, ajustar ou encerrar, com evidências favoráveis
   e contrárias, limites da amostra e custo de expansão. Não prometer ganho
   percentual antes da baseline nem condicionar a honestidade do relatório a
   encontrar um resultado positivo.

## 9. Decisões e execução do backlog da semana 1

- Validar a distribuição das 40 h/semana de engenharia, a premissa de cinco dias
  úteis e as agendas do gerente/participantes.
- Confirmar quando e por quem a amostra pode ser liberada e sanitizada.
- Aceitar ou ajustar o recorte e a alocação semanal de revisão.
- Aprovar o protocolo de baseline/comparação, classificação documental e regra
  de interrupção; metas numéricas dependem da semana 1.
- Definir quem decide bloqueios, mudanças de escopo e aceite final do experimento.

O [registro](business-poc-decisions-dependencies.md) identifica responsáveis por
papel, datas relativas necessárias e consequências dos atrasos. O
[backlog da semana 1](business-poc-week1-backlog.md) estima 36 h de trabalho e 4 h
de reserva, separando itens iniciáveis de bloqueados. É proposta de planejamento,
não autorização presumida para dados, participantes ou execuções de modelo.
O cenário não atualiza retrospectivamente o aceite da V1: fornece uma nova
referência simulada para avaliar reaproveitamento e mudanças. Não houve mudança
de código, de anotações ou de configurações; o experimento pendente anterior
permanece fora desta entrega. Sem commit ou push.
