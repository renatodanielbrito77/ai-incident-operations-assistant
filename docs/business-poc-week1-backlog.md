# Backlog proposto — semana 1 da POC simulada

Data: 2026-11-04. Base: [proposta](business-poc-four-week-proposal.md),
[decisões/dependências](business-poc-decisions-dependencies.md) e
[cenário simulado](scenarios/business-demand-simulated.md).

## Objetivo e orçamento

Decidir se a POC pode prosseguir com amostra autorizada, controles definidos e
baseline manual, ou documentar objetivamente por que não pode. Não implementar
a nova solução antes dessa decisão e não simular resultado de valor de Negócios.

**Uma pessoa de engenharia com Codex, 40 h no total: 36 h estimadas de trabalho
mais 4 h de reserva.** As estimativas incluem análise, preparação, revisão,
coordenação, registro e trabalho com a IA. Não são horas líquidas de codificação
nem pressupõem multiplicador de produtividade. Os dois spikes estão dentro das
36 h; não devem ser cobrados novamente na reserva.

Todos os itens estão **não iniciados** para esta semana de projeto. “Iniciável”
significa que a preparação pode usar a V1/documentos atuais, não que aprovações
externas já existam. As datas são relativas a T0 a confirmar, sem calendário
ou participantes nominais inventados. Itens bloqueados só começam após evidência
de liberação das dependências.

## Estado inicial e primeira ação proposta

O grupo A dispensa dados novos, mas seus itens não estão todos prontos para
começar simultaneamente: W1-06 aguarda o rascunho W1-03, e W1-12 consolida o que
estiver disponível ao fim da semana. Nenhum item foi iniciado ou concluído por
este planejamento.

| ID | Título resumido | Horas | Dependências principais | Estado inicial |
|---|---|---:|---|---|
| W1-01 | Confrontar V1 e demanda | 3 | V1 e cenário documentados | Pronto para iniciar |
| W1-02 | Preparar confirmação de responsáveis e agendas | 3 | Papéis do cenário; obter respostas de D01–D03 | Pronto para iniciar a preparação; confirmações externas pendentes |
| W1-03 | Desenhar medição e revisão prévia | 4 | Cenário e ajustes; D06 é aceite posterior | Pronto para rascunhar |
| W1-04 | Preparar recebimento e classificação | 3 | Sem acesso novo; D02/D04/D05 para preenchimento real posterior | Pronto para preparar modelos vazios |
| W1-05 | Definir matriz de proteção e encaminhamento | 3 | V1 e demanda; D06/D08 para casos concretos posteriores | Pronto para rascunhar |
| W1-06 | Preparar fichas e rastreabilidade | 2 | W1-03; D02 antes de usar dados | Aguardando rascunho W1-03 |
| W1-07 | Spike S1: dados e classificação | 2 | D02/D04/D03 | Bloqueado por autorização, amostra e agenda |
| W1-08 | Preparar recorte sanitizado | 3 | W1-07; D02/D04/D05 | Bloqueado por dados e classificação |
| W1-09 | Preparar referência e validar protocolo | 3 | W1-03/W1-08; D03/D05; produzir D06/D08 | Bloqueado por dados e revisão do especialista |
| W1-10 | Spike S2: utilidade e viabilidade local | 2 | W1-07/W1-08; D02/D03/D06; permissão e ambiente | Bloqueado por dados, agenda e liberação do ensaio |
| W1-11 | Observar baseline manual | 4 | W1-06/W1-09; D02/D03/D08 | Bloqueado por dados, referências e agendas |
| W1-12 | Consolidar semana e solicitar decisão | 4 | Resultados disponíveis e bloqueios; D10 para aceite | Planejado para fechamento da semana; não depende de fingir dados recebidos |

**Primeiro item recomendado: W1-02.** Preparar a confirmação de responsáveis,
datas e agendas expõe cedo os bloqueios que engenharia não resolve sozinha e
protege o prazo de quatro semanas. Não exige acesso aos dados e não depende de
enviar mensagens ou marcar reuniões sem autorização. Após essa preparação,
seguir com W1-01 enquanto as confirmações externas são aguardadas.

## A. Iniciáveis sem dados novos ou agenda confirmada — 22 h

| ID | Objetivo | Resultado verificável | Dependências | Engenharia (h) | Critério de conclusão |
|---|---|---|---|---:|---|
| W1-01 | Confrontar a V1 com a demanda e os controles essenciais | Mapa curto de reaproveitamento, lacunas e fronteiras, com referências aos módulos existentes | V1 e cenário já documentados; não exige dados novos | 3 | Documento distingue proteção P1, elegibilidade documental e revisão humana de melhorias opcionais; não declara reconhecimento geral de conflito/insuficiência ou capacidades não implementadas |
| W1-02 | Preparar confirmação de responsáveis, agenda e datas de decisão | Registro D01–D12 com solicitações/propostas de agenda, donos por papel e prazo necessário | Papéis do cenário; respostas de D01/D02/D03 continuam externas e não são presumidas | 3 | Cada dependência tem responsável por obter resposta, data relativa e consequência. Solicitação preparada ou emitida é distinguida de aceite; ausência de resposta permanece aberta |
| W1-03 | Desenhar medição e revisão prévia | Protocolo em rascunho: limites, início/fim, esforço por papel, rubrica, critérios de interrupção e distribuição das sessões | Cenário e ajustes do usuário; aprovação depende de D06, fora da conclusão deste rascunho | 4 | Especifica quatro sessões manuais e quatro assistidas finais; inclui espera/revisão/correções e resultados censurados; não apresenta metas ou rubrica como aprovadas |
| W1-04 | Preparar recebimento e classificação da amostra | Checklist de entrega/sanitização e modelo vazio de manifesto com campos de origem, versão, status e autorização | Nenhum acesso novo; preenchimento real depende de D02/D04/D05 | 3 | Modelo separa anunciado de recebido, ativo/descontinuado/não confirmado e dados construídos de recebidos; não atribui status a documentos inexistentes |
| W1-05 | Definir a matriz dos caminhos de proteção e encaminhamento | Plano de verificação para P1, documento descontinuado, ausências de checklist, conflito previamente identificado, erro e abstenção | Limites da V1 e demanda; casos concretos e referências dependem de D06/D08 | 3 | Cada caminho tem resultado observável esperado, controle essencial e evidência a coletar; não contém teste executado ou detecção semântica geral prometida |
| W1-06 | Preparar coleta e rastreabilidade das sessões | Fichas vazias para tempos, entrada/saída, revisão prévia, correções, bloqueios e relatório do analista | Protocolo em rascunho W1-03; uso de dados depende de D02 | 2 | Ficha preserva original e revisão humana separados; registra modalidade, papel, fila, falha, conclusão/incompleto e fonte. Regras de retenção ficam marcadas como pendentes se não autorizadas |
| W1-12 | Consolidar a semana e formular a decisão solicitada | Parecer de continuar, reduzir ou inviabilidade com horas reais, bloqueios e impacto no prazo; ata/proposta de decisão de Negócios | Todos os resultados disponíveis, inclusive ausência de dados; aceite do gerente é D10, não pressuposto | 4 | Parecer emitido até S1D5 com evidências ou ausência delas. Decisão sem resposta permanece “solicitada”, sem aceite fabricado. A conclusão deste item não encerra itens bloqueados nem prorroga o prazo |
| | **Subtotal iniciável** | | | **22** | |

W1-12 é concluível como parecer de bloqueio mesmo sem baseline; não como medição
realizada. O rascunho do protocolo ou a leitura prévia da V1 não substituem a
aprovação dos participantes ou a baseline. Não enviar solicitações ou marcar
reuniões automaticamente por causa deste documento.

## B. Bloqueados por dados, autorização ou agenda — 14 h

| ID | Objetivo | Resultado verificável | Dependências que bloqueiam | Engenharia (h) | Critério de conclusão |
|---|---|---|---|---:|---|
| W1-07 | Spike S1: verificar viabilidade dos dados e da classificação | Inspeção delimitada de amostra liberada, com problemas de ligação/formato, estado documental e decisão de viabilidade | D02 autorização; D04 recebimento; D03 janela do especialista | 2 | Dentro do timebox, registrar o que foi efetivamente recebido e validado, campos/status pendentes e decisão técnica. Timebox sem conclusão registra incerteza; não equivale a liberação. Sem amostra, permanece bloqueado, não “concluído com mocks” |
| W1-08 | Preparar recorte e fichas com dados sanitizados | Manifesto do subconjunto e mapeamento dos campos para a V1, com limitações por fonte; sem ingestão/código novo nesta semana | W1-07; D02/D04; classificação de D05 para documentos elegíveis | 3 | IDs, origem, período, versão/status e permissão rastreáveis. Campo desconhecido permanece desconhecido; volume selecionado pode ser menor que o teto da proposta |
| W1-09 | Preparar referência da baseline e validar o protocolo | Casos de baseline e checklists revisados pelo especialista; decisões sobre C03/revisão prévia, D06 e D08 registradas | W1-03/W1-08; D03 agenda e D05 classificação. D06/D08 são deliberações a produzir, não pré-requisitos já aprovados | 3 | Referências de próximas verificações, sem hipóteses de causa; campos mínimos e conflitos limitados a casos definidos; aceite ou objeções identificados. Sem revisão, não usar como referência validada |
| W1-10 | Spike S2: verificar utilidade/viabilidade local em poucos casos de desenvolvimento | Registro controlado de tempo, contexto, resposta e revisão, com uma conclusão de continuar/ajustar/parar | W1-07/W1-08; D02 autorização; D03 especialista; D06 segurança; permissão para ensaio e ambiente/modelo disponíveis a confirmar | 2 | Resultado e falhas registrados no timebox, sem reparação/retry para obter saída favorável. Ausência de recursos ou de ensaio é bloqueio, não resultado positivo. Não executar nesta entrega de planejamento |
| W1-11 | Observar baseline manual dos dois analistas | Até quatro sessões manuais exploratórias: dois casos por analista, fichas de tempo, cobertura, escalonamento e feedback | W1-06/W1-09; D02 dados permitidos; D03 agendas; D08 casos aprovados | 4 | Sessões e limites efetivamente registrados, incluindo incompletas; se faltar participante/dado, registrar quantas ocorreram e a lacuna. Não inferir metas ou baseline a partir da V1 mockada |
| | **Subtotal condicionado** | | | **14** | |

Na sequência pretendida, W1-07 começa após recebimento necessário em S1D2;
W1-08 e W1-09 preparam sessões até S1D3–S1D4; W1-10 depende de liberação para
ensaio, e W1-11 da agenda e referências. A sequência não garante que o dado ou
a reunião chegarão a tempo. Nenhuma atividade bloqueada foi iniciada aqui.

## C. Reserva e total

| Componente | Engenharia (h) |
|---|---:|
| Itens iniciáveis — W1-01 a W1-06 e W1-12 | 22 |
| Itens condicionados — W1-07 a W1-11 | 14 |
| Reserva da semana 1 | 4 |
| **Teto da semana** | **40** |

A reserva é 10% da semana; as quatro semanas reservam 16 h de 160 h. Ela não é
uma tarefa concluída nem usada por padrão. Registrar motivo, autorização e horas
consumidas. Espera externa não é convertida automaticamente em esforço executado.
Capacidade bloqueada não deve ser gasta em funcionalidades novas sem decisão de
priorização; pode permanecer não utilizada e deve ser reportada como tal.

Se a reserva se esgotar: primeiro cortar melhorias de apresentação não essenciais;
depois reduzir o recorte/amostra com declaração da limitação, preservando equilíbrio
entre modalidades quando possível e casos de proteção. Manter controles essenciais
e a avaliação/decisão final. Sem capacidade para esses mínimos, produzir parecer
ou negociar formalmente; não ampliar horas ou prazo automaticamente.

## D. Tempo dos demais participantes — não incluído nas 40 h de engenharia

| Papel | Alocação máxima proposta na semana 1 | Itens relacionados |
|---|---|---|
| Especialista | 1 h S1/dados/status; 1,5 h referências dos casos; 0,5 h aprovação da rubrica; 0,5 h S2; 0,5 h alinhamento/decisão semanal. **Total: 4 h** | W1-07, W1-09, W1-10 e W1-12 |
| Analista iniciante | 0,5 h orientação; 1 h para dois casos manuais; 0,5 h feedback. **Total: 2 h** | W1-11 |
| Analista experiente | Mesma distribuição. **Total: 2 h** | W1-11 |
| Gerente | Alinhamento/decisão proposto de até 30 min; duração e respostas necessárias ainda a confirmar | D01–D03, D10/D12 e W1-02/W1-12 |

O especialista não ganha horas extras para corrigir dados ou revisar todo o acervo.
As classificações não resolvidas no timebox continuam pendentes. W1-08 organiza
resultados já validados; não pressupõe uma nova revisão do especialista fora do
orçamento. As horas de analistas são da baseline, não incluem sessões finais que
só ocorreriam na semana 4.

## E. Aceite da semana e contingência de prazo

Semana tecnicamente pronta para prosseguir requer amostra autorizada, recorte
e classificação utilizáveis, rubrica/encaminhamento de P1 acordados e resultados
dos spikes registrados. A baseline só é declarada se ocorreu; sem ela, a avaliação
comparativa e as metas ficam pendentes e o gerente precisa deliberar o alcance.

S1D2: escalar ausência de liberação/amostra. Até S1D5: registrar a decisão
solicitada sobre continuidade, redução ou inviabilidade. O parecer e as
pendências são entregáveis honestos; não representam sucesso da hipótese de valor.
O prazo original termina em S4D5, salvo renegociação explícita com Negócios.
Sem essa renegociação, uma demonstração técnica reduzida exige objetivo aceito;
se não houver aceite, entregar o parecer de inviabilidade/pendências, sem declarar
o objetivo original cumprido.

Este documento é backlog proposto, não evidência de acesso, participantes
confirmados, tarefas realizadas ou resultados obtidos. Nenhum código foi
implementado, modelo chamado ou dado externo acessado nesta elaboração.
