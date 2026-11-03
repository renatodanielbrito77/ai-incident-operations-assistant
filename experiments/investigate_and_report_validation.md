# Validação controlada da CLI de investigação e relatório

Data: 2026-11-03. Registro retrospectivo; nenhuma investigação ou geração nova foi
executada para esta revisão. Revisão qualitativa assistida para avaliação humana,
sem aprovação semântica automática.

## Escopo e implementação

- [CLI](investigate_and_report.py) e [testes](test_investigate_and_report.py).
- Reutiliza `build_llm_input_package`, `serialize_llm_input_package`, o executor
  experimental `run_experiment` e `render_candidate_report`; não recalcula regras
  estruturais nem importa `main.py`, embeddings ou juiz semântico.
- Candidata e relatório estrutural válidos são necessários para chamar o gerador
  de relatório de candidata. Inelegibilidade e erros recebem resumo próprio,
  sem fabricação desses objetos.
- `NOT_ELIGIBLE` usa código 0 sem produzir candidata: o consumidor deve consultar
  `final_state` e `candidate_produced`, não apenas o código do processo.
- Código 1 distingue rejeição estrutural; código 2 indica falha na investigação,
  contexto, geração ou gravação de artefatos. O código original do executor de
  geração é preservado separadamente.

## Ambiente, parâmetros e controle de chamadas

Foi usada a imagem existente `ai-incident-operations-assistant-ai-app`, com o
projeto montado somente para leitura na rede
`ai-incident-operations-assistant_default`. Não houve build ou reinício.

- API: `http://ai-app:8000`; Ollama no Mac: `http://host.docker.internal:11434`.
- As duas URLs são opções da CLI; `127.0.0.1` dentro do container aponta para o
  próprio container, não para o Mac ou outro serviço do Compose.
- Investigação: timeout 30 segundos.
- Geração: `qwen3:1.7b`, `num_ctx=4096`, `num_predict=256`, temperatura 0,
  timeout 120 segundos, `keep_alive=0`.
- `truncate=false`, `shift=false`, `think=false`, `stream=false`.
- Instruções oficiais atuais, política `1.0`; nenhuma instrução experimental
  revisada foi acrescentada e o orçamento não foi elevado automaticamente.

A CLI foi executada por um driver temporário que chamou `main` com as URLs
acima e contou os transportes HTTP reais. A barreira permitiu zero chamadas ao
Ollama no primeiro lote, INC-002 e INC-003, e no máximo uma no segundo, INC-001.
Cada incidente recebeu um diretório novo. Não houve repetição ou reparação.

## Resultados reais

| Incidente | Estado final | Código | Motivo | Candidata produzida | Chamadas Ollama |
|---|---|---:|---|---|---:|
| INC-002 | `NOT_ELIGIBLE` | 0 | `P1` | `false` | 0 |
| INC-003 | `NOT_ELIGIBLE` | 0 | `ABSTAINED` | `false` | 0 |
| INC-001 | `STRUCTURAL_CHECKS_PASSED` | 0 | `STRUCTURE_EVALUATED` | `true` | 1 |

INC-002 e INC-003 retornaram HTTP 200 da investigação, sem montar pacote nem
acionar o executor de geração. Seus `report.md` são resumos de inelegibilidade.
INC-001 retornou HTTP 200 e contexto elegível, permitindo uma única geração.

| Indicador da geração de INC-001 | Resultado |
|---|---|
| HTTP / conclusão | 200 / `done=true`, `done_reason="stop"` |
| Tempo observado pelo cliente | 11.931 segundos |
| Tokens de entrada / saída | 1887 / 172 |
| Modelo retornado | `qwen3:1.7b` |
| Referências | `REFERENCES_IN_CONTEXT`, `invalid_chunk_ids=[]` |
| Ação declarada | `observe`, `ACTION_TYPE_ALLOWED` |
| Resultado estrutural | `structural_checks_passed=true` |
| Sustentação semântica automática | `not_evaluated` |

A entrada mais a reserva completa de saída foi `1887 + 256 = 2143`, dentro do
contexto 4096. Não houve limite de geração atingido ou ajuste automático.

## Correlação do audit

| Incidente | `audit_event_id` da resposta e do resultado da CLI |
|---|---|
| INC-002 | `e6f78009-154b-4afb-adf4-cf16fdbd98c2` |
| INC-003 | `a1a60b72-30b4-402e-8020-e641409fcfa5` |
| INC-001 | `05a12edb-8da4-4e7d-9690-f7d883dcaa47` |

Para cada ID foi localizado exatamente um evento, com `incident_id` correspondente.
Em INC-001, o ID foi preservado também no pacote e no pacote salvo pelo executor.
As evidências do pacote foram conferidas como iguais ao corpo da investigação;
nenhum novo identificador foi gerado pela CLI. O volume de audit foi montado
somente para leitura no container de validação. Apenas a API realizou as gravações
normais das três investigações; a CLI não acrescentou eventos.

## Candidata integral de INC-001

```json
{
  "text": "A análise do incidente de timeout no checkout revela que os sinais observáveis incluem logs de erro e aviso, status de monitoramento de degradação e métricas de latência elevadas. Os dados insuficientes indicam que a causa raiz não foi comprovada, e a orientação sugere investigar a dependência do serviço de pagamentos. O runbook é relevante para os sinais observáveis, mas não autoriza ações de reinício ou configuração automática.",
  "action_type": "observe",
  "cited_chunk_ids": [
    "RB-001-02-01",
    "RB-001-03-02",
    "RB-001-04-02"
  ]
}
```

## Revisão do conteúdo do relatório

A revisão abaixo confronta a candidata com o pacote efetivamente usado. Não
modifica o texto original nem o resultado estrutural.

| Afirmação ou aspecto | Evidência disponível e citações | Revisão |
|---|---|---|
| “logs de erro e aviso, status de monitoramento de degradação e métricas de latência elevadas” | Logs atuais ERROR e WARN; monitoring `degraded`, p95 de 1800 ms. `RB-001-02-01`, citado, descreve esses sinais. | Sustentado pelos dados atuais. Não foram identificados valores ou registros inventados nessa descrição. |
| “Os dados insuficientes indicam que a causa raiz não foi comprovada” | O contexto não demonstra causa raiz. `RB-001-03-02`, citado, contém a condição “Se não houver informações suficientes”. | Formulação imprecisa: não identifica quais dados faltam e apresenta insuficiência de modo genérico. A regra documental não comprova sozinha essa insuficiência nem uma avaliação formal realizada. Diferentemente de uma candidata anterior, não afirma que dados faltantes foram registrados. |
| “a orientação sugere investigar a dependência do serviço de pagamentos” | `RB-001-04-02`, citado, exige timeouts recorrentes acompanhados de degradação e orienta consultar monitoring e logs de pagamentos. | A sugestão omite condições e a verificação concreta. Há degradação, mas apenas um log explícito de timeout; o WARN de excesso de latência não comprova outro timeout. A recorrência não está demonstrada no recorte atual. |
| Dados necessários à investigação de pagamentos | O pacote contém monitoring e logs de checkout; monitoring e logs do serviço de pagamentos não foram fornecidos. `RB-001-04-02` orienta explicitar a limitação quando esses dados não estiverem disponíveis. | A candidata não delimita essa lacuna. Não se deve afirmar que os dados não existem ou que não foram coletados fora do contexto. |
| “não autoriza ações de reinício ou configuração automática” | Restrição sustentada por `RB-001-05`, disponível em `document_limits`, mas não citado pela candidata. | Há suporte disponível, porém falta citação do trecho que sustenta essa restrição. Os três chunks citados não contêm essa proibição explícita. O relatório existente mostra somente chunks citados; não acrescentou Limites para corrigir a candidata. |
| Uso dos históricos | HIST-001 e HIST-002 estavam no contexto, separados da documentação. | Não há uso indevido explícito: a candidata não propõe repetir resolução histórica, reverter configuração ou atribuir ao caso atual o resultado de um incidente passado. Isso não prova ausência de influência dos históricos no processamento interno do modelo. |

Conclusão qualitativa: há fatos atuais sustentados e uma direção de investigação
pertinente ao runbook, mas faltam precisão sobre dados ausentes, preservação da
condição de recorrência e citação dos Limites utilizados. A passagem estrutural
não elimina esses problemas nem aprova o conteúdo para execução. Não se concluiu
uma causa raiz e nenhuma ação foi executada.

## Testes isolados e revisão final

```bash
docker run --rm --network none \
  --mount type=bind,source="$PWD",target=/workspace,readonly \
  --workdir /workspace/experiments \
  ai-incident-operations-assistant-ai-app \
  python -B -m unittest -q test_investigate_and_report test_send_package_to_ollama
```

Resultado da revisão final: **40 testes passaram**, sem rede e sem novas chamadas
reais. São 20 testes da CLI e 20 do executor reutilizado. Cobrem encerramentos sem LLM,
HTTP/transportes, contexto inconsistente, candidata e relatório inválidos,
rejeição estrutural, preservação de artefatos, falha de gravação, URLs
configuráveis e ausência de import de API/embeddings/audit/juiz semântico.
A mensagem `Erro operacional: disk full` é esperada no teste simulado de gravação,
não uma falha real do disco.

## Artefatos e limitações

Originais locais preservados, fora do Git:
`/private/tmp/investigate-cli-live.rX7bfY/`.
Cada subdiretório INC-002, INC-003 e INC-001 contém resposta bruta de investigação,
metadados, parâmetros, resultado, relatório e registro da validação controlada.
Somente INC-001 contém pacote e artefatos de geração. O driver e os registros de
contagem de chamadas são temporários; não foram incluídos no repositório.

- Uma chamada por incidente e apenas uma geração; não demonstra qualidade geral
  das candidatas, estabilidade ou resistência a instruções maliciosas.
- A falta de recorrência demonstrada neste recorte não comprova que timeouts não
  se repetiram em outro período. Os históricos não substituem essa evidência atual.
- O caminho real de falta de logs e os caminhos reais de erro/rejeição estrutural
  não foram exercitados nesta rodada; possuem cobertura isolada com mocks.
- Modelos/contratos e referências válidas não garantem suporte semântico ou
  coerência entre texto e tipo de ação declarado.
- As contagens e os tempos são específicos desta execução. Os artefatos locais
  podem desaparecer após limpeza de temporários; este registro não os substitui
  como arquivo integral de dados brutos.
- API, audit, política, parâmetros oficiais, índices e configurações persistentes
  permaneceram inalterados. Os mesmos containers de ai-app, Mock Services e
  Qdrant permaneceram em execução. Nenhuma geração foi repetida nesta revisão.
