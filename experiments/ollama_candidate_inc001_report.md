# Experimento: candidata a partir do contexto de INC-001

Execução: 2026-11-03, resposta concluída às 18:13:02 UTC (15:13:02 em São Paulo).
Relatório retrospectivo: nenhuma nova geração foi executada para produzi-lo.

## Objetivo e entrada

Enviar o pacote completo e validado de `INC-001` ao Ollama e verificar a conclusão,
o contrato da candidata e suas referências e ação declarada. A sustentação
semântica permanece fora das verificações automáticas.

- Script: [send_package_to_ollama.py](send_package_to_ollama.py).
- Modelo local: `qwen3:1.7b`. Ollama `0.40.14` confirmado no teste de
  compatibilidade anterior; o script não consultou a versão nesta execução.
- Pacote `CONTEXT_READY`: 8.019 caracteres, 8.137 bytes UTF-8.
- `audit_event_id` preservado: `afc36a70-04a9-4039-9631-d8820c2f115c`.
- Instruções no campo `system`; evidências e identificadores no campo `user`.
  A reconstrução dos campos das mensagens corresponde ao pacote completo.
- Documentação: `RB-001-02-01`, `RB-001-03-02`, `RB-001-04-02`.
- Limites: `RB-001-05`. Históricos: `HIST-001` e `HIST-002`.

## Parâmetros e execução

| Parâmetro | Valor |
|---|---|
| Endpoint | `http://host.docker.internal:11434/api/chat` |
| `num_ctx` | `4096` |
| `num_predict` | `256` |
| Timeout total | 120 segundos |
| `temperature` | `0` |
| `truncate`, `shift`, `think`, `stream` | Todos `false` |
| `keep_alive` | `0` |
| `format` | `RecommendationCandidate.model_json_schema()` |

Os 20 testes isolados passaram no container com `--network none` antes da
única chamada real. Não houve reparo, repetição, aumento de limites, truncamento
de evidências, consulta adicional de chunks ou execução de ações. A resposta
HTTP foi preservada antes de validar a candidata. API e audit não foram alterados
nem acionados pelo script; o pacote utilizado já estava salvo.

## Resultado observado

| Indicador | Resultado |
|---|---|
| HTTP / código de saída | `200` / `0` |
| Tempo observado pelo cliente | 17,866 s |
| Tempo total informado pelo Ollama | 17,509 s |
| Carregamento do modelo | 6,472 s |
| Avaliação da entrada / geração | 6,894 s / 3,767 s |
| Tokens de entrada / saída | 1.893 / 167 |
| Tokens de entrada em cache | 0 |
| Conclusão | `done=true`, `done_reason="stop"` |
| Thinking retornado | Nenhum |

A contagem de entrada mais a reserva de geração foi `1893 + 256 = 2149`,
inferior ao contexto de 4.096. O teste anterior com entrada sintética excessiva
e contexto de 256 tokens retornou HTTP 400 explícito no Ollama `0.40.14`.
Essa evidência, os controles contra corte e a preservação integral das mensagens
fundamentam a verificação; `prompt_eval_count` isoladamente não prova ausência
de truncamento. O esgotamento do contexto durante uma geração longa não foi
exercitado neste caso.

## Candidata retornada integralmente

```json
{
  "text": "A análise do incidente de aumento de erros no checkout revela que os sinais observáveis incluem logs de erro e aviso com mensagens específicas, assim como métricas de monitoramento degradadas. O runbook indica que a recomendação é investigar a dependência do serviço de pagamentos e verificar logs do serviço para identificar a causa raiz. Dados insuficientes foram registrados, e a falta de logs não comprova ausência de falha.",
  "action_type": "request_verification",
  "cited_chunk_ids": [
    "RB-001-02-01",
    "RB-001-03-02",
    "RB-001-04-02"
  ]
}
```

## Verificações estruturais e revisão do conteúdo

O JSON e o contrato Pydantic passaram. As regras existentes retornaram:

- Referências: `accepted=true`, `REFERENCES_IN_CONTEXT`, `invalid_chunk_ids=[]`.
- Ação declarada: `allowed=true`, `ACTION_TYPE_ALLOWED`.
- Resultado conjunto: `structural_checks_passed=true`.
- Sustentação semântica automática: **`semantic_support_status="not_evaluated"`**.

A revisão qualitativa abaixo foi registrada nesta entrega para revisão humana;
não representa aprovação explícita do usuário nem uma avaliação semântica
automática adicionada ao sistema.

| Trecho ou aspecto | Revisão baseada somente no pacote fornecido |
|---|---|
| Logs de erro/aviso e métricas degradadas | Sustentado pelos dois logs de checkout, status `degraded`, taxa de erros de 12,5% e latência p95 de 1.800 ms; compatível com `RB-001-02-01`. |
| Investigar a dependência de pagamentos | Compatível com `RB-001-04-02`. A candidata menciona logs, mas omite a solicitação explícita de monitoring de pagamentos também indicada no trecho. |
| “Dados insuficientes foram registrados” | Afirmação sem suporte demonstrado: `RB-001-03-02` orienta registrar dados faltantes **se** forem insuficientes; não comprova que tal registro aconteceu. É uma passagem indevida de orientação condicional para fato afirmado. |
| “A falta de logs não comprova ausência de falha” | A ressalva existe em `RB-001-05`, fornecido no contexto, mas não citado pela candidata. Há logs de checkout; o pacote não contém logs/monitoring de pagamentos. A frase deveria distinguir essa limitação, sem sugerir ausência geral de logs. |
| Causa raiz e mudanças de ambiente | O texto não afirma uma causa raiz específica nem solicita mudança de ambiente. Isso não transforma a passagem estrutural em autorização de execução. |

Conclusão da revisão: o texto contém orientação pertinente, mas precisa de ajuste
humano antes de ser apresentado como orientação revisada, especialmente na
afirmação sobre dados insuficientes. A candidata original foi mantida sem edição.
O experimento demonstra que referências presentes e ação declarada permitida
podem coexistir com afirmações não sustentadas.

## Artefatos e limitações

Originais locais: `/private/tmp/ollama-package-run.15AWw3/run/`:
`package.json`, `parameters.json`, `request.json`, `input_metadata.json`,
`response.body`, `response_http.json`, `candidate.json` e `result.json`.
Esses arquivos temporários não são incluídos nem modificados por este relatório
e podem deixar de existir após limpeza do sistema.

- SHA-256 do pacote: `2f9b6b6ac115b8d55a5fb7a26fdc634e343f6c1728e6706b219fb0ac9b9db8de`.
- SHA-256 da requisição: `af28fcd7deccc142a9f981f0ed5e7d8ac7237796b8fa0338b8c3fc206ae2deaa`.

Apenas uma geração, um incidente e um runbook foram avaliados. Não há medição de
qualidade geral, reprodutibilidade, resistência a instruções maliciosas nos dados
ou aprovação semântica automática. O resultado não autoriza execução de ações.
