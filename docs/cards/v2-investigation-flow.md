# Card — investigação V2 temporal e documental

## Objetivo

Conectar o recorte sintético checkout ao controle documental existente, encerrando P1 antes das dependências documentais e solicitando evidências aplicáveis antes da recuperação.

## Estado

Implementação e testes isolados concluídos. Demonstração real no Qdrant **concluída**, com os quatro estados esperados e código 0; [registro e limitações](../investigation-v2-demonstration.md). Sem LLM ou alteração de API/audit/V1. Entrega preparada para versionamento; artefatos operacionais externos permanecem fora do Git.

## Critérios verificados

- P1 não acessa provedores de evidências/históricos, encoder ou fábrica documental.
- Fusos equivalentes e extremos inclusivos; timestamps inválidos/sem fuso são erros de contrato.
- Logs vazios, antigos e mistos têm caminhos distintos; histórico/busca usam somente logs aplicáveis.
- Métricas antigas são preservadas e impedem pacote até receber o período correto.
- Pacote mantém evidências, ordem, metadados e identificador recebido.
- Somente documentos ativos e Limites da mesma versão fundamentam o contexto.
- Integridade e bloqueio são erros distintos de ausência documental.
- Regressão do controle documental e empacotamento anterior incluída na execução delimitada.

## Evidências e esforço

Comando reproduzível e escrita prevista: [especificação](../investigation-v2-specification.md).
Execução final em 2026-11-06: **88 testes aprovados**, código de saída **0**, em **0,611 s** reportados pelo unittest. São 33 testes novos e 55 de regressão. Esta duração é apenas a do runner, não esforço de engenharia.
Primeira rodada identificou sombreamento de import no empacotamento anterior; corrigido antes da repetição.
Esforço humano efetivo **não medido**: não transformar estimativa ou duração dos testes em horas trabalhadas.

## Limitações preservadas

Teste funcional com backend/vetores controlados não demonstra relevância semântica. Lote de desenvolvimento não é baseline nem comparação com participantes. A CLI usa marcador de audit sintético, sem persistência. Lock/estado dependem de acesso pelo componente e caminho canônico; acesso direto ao Qdrant permanece fora dessa proteção. Nenhum encaminhamento envia notificações.
