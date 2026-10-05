# RB-001 — Timeout na comunicação entre checkout e pagamentos

## Objetivo

Orientar a investigação de incidentes não-P1 relacionados à lentidão ou a erros na comunicação entre a aplicação `checkout` e o serviço de pagamentos.

Este documento e seus limiares são fictícios, criados para a POC. Não representam procedimentos validados de produção.

## Sintomas

Este runbook pode ser relevante quando houver um ou mais destes sinais:

- Log de nível `ERROR` com a mensagem `Timeout while connecting to payment service`.
- Log de nível `WARN` com a mensagem `Payment request exceeded latency threshold`.
- Monitoring da aplicação `checkout` com status `degraded`.
- Taxa de erros acima de 5%.
- Latência p95 acima de 1.000 ms.

Os limiares de 5% e 1.000 ms são regras fictícias deste exercício. Um sinal isolado não comprova a causa do incidente.

## Verificações

Antes de recomendar uma ação, o operador deve:

1. Confirmar que o incidente pertence à aplicação `checkout` e não é P1.
2. Conferir se os logs e as métricas correspondem ao período do incidente.
3. Verificar se os timeouts se repetem ou representam um evento isolado.
4. Comparar a taxa de erros e a latência com períodos anteriores.
5. Verificar a saúde do serviço de pagamentos, caso essa informação esteja disponível.
6. Consultar incidentes históricos semelhantes, quando houver acesso a esses dados.

Se não houver informações suficientes, registrar quais dados faltam. Não presumir que o serviço de pagamentos está indisponível apenas porque o checkout registrou um timeout.

## Orientações

### Acompanhar a evolução

Quando houver um evento isolado e as métricas estiverem se recuperando, recomendar acompanhamento da taxa de erros, da latência e da ocorrência de novos timeouts.

### Investigar a dependência de pagamentos

Quando houver timeouts recorrentes acompanhados de degradação das métricas, recomendar a consulta ao monitoring e aos logs do serviço de pagamentos.

Se esses dados não estiverem disponíveis, informar a limitação e solicitar sua verificação pelo responsável.

### Escalar para um responsável

Quando a degradação persistir ou houver evidência de impacto nas transações, recomendar avaliação pelo responsável por checkout e, conforme as evidências, pelo responsável pelo serviço de pagamentos.

A recomendação deve incluir os sinais observados e as verificações ainda pendentes.

## Limites

- Este runbook não se aplica a incidentes P1, que devem seguir o fluxo de escalonamento manual da POC.
- Não autoriza reinícios, alterações de configuração, reprocessamento de pagamentos ou outras mudanças automáticas.
- Não permite concluir a causa raiz somente a partir das mensagens de timeout.
- Ausência de logs não comprova ausência de falha.
- Dados ausentes ou fora do período do incidente devem ser explicitados como limitações.

## Evidências esperadas na recomendação

Uma recomendação baseada neste runbook deve apresentar:

- Identificador do incidente e aplicação afetada.
- Mensagens de log relevantes.
- Taxa de erros, latência p95 e status observados.
- Relação entre as evidências e a orientação escolhida.
- Dados faltantes e verificações pendentes.
- Referência ao documento `RB-001`.