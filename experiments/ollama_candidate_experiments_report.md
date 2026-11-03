# Experimentos Ollama: instruções e orçamento de saída

Data: 2026-11-03. Consolidação retrospectiva de três chamadas únicas já concluídas.
Nenhuma geração foi repetida para produzir este relatório.

## Objetivo e controle experimental

Comparar instruções originais com instruções adicionais para separar fatos de
verificações e, depois, mudar somente o orçamento de saída. Os três experimentos
usaram o mesmo pacote completo de `INC-001`, sem consultar novamente a API.

- Modelo: `qwen3:1.7b`, já instalado; Ollama `0.40.14` confirmado previamente.
  O script não consulta a versão a cada execução.
- Contexto: `4096`; temperatura: `0`; timeout: `120` segundos; `keep_alive=0`.
- `truncate=false`, `shift=false`, `think=false`, `stream=false`.
- Mesmo schema `RecommendationCandidate`, mesmas validações de conclusão,
  contrato e estrutura; sem reparos, retries ou aumento automático de limites.
- Pacote: 8.019 caracteres, 8.137 bytes UTF-8; mesmo conteúdo e ordem das evidências.
- `audit_event_id`: `afc36a70-04a9-4039-9631-d8820c2f115c`.
- SHA-256 do pacote: `2f9b6b6ac115b8d55a5fb7a26fdc634e343f6c1728e6706b219fb0ac9b9db8de`.
- Instruções em `system`; evidências e identificadores em `user`.
- Documentação citável: `RB-001-02-01`, `RB-001-03-02`, `RB-001-04-02`;
  Limites: `RB-001-05`; históricos: `HIST-001`, `HIST-002`.

| Experimento | Instruções | `num_predict` |
|---|---|---:|
| E1 | Originais do pacote | 256 |
| E2 | Originais + adicionais transcritas abaixo | 256 |
| E3 | Mesmas de E2 | 512 |

## 1. Conclusão da geração

Todos retornaram HTTP 200, `done=true`, `done_reason="stop"` e nenhum thinking.
Esses sinais do servidor devem ser distinguidos das barreiras do cliente.

| Execução | Conclusão UTC | Tempo do cliente (s) | Tokens de entrada | Tokens de saída | Código de saída |
|---|---|---:|---:|---:|---:|
| E1 | 2026-11-03T18:13:02.618063Z | 17.866 | 1893 | 167 | 0 |
| E2 | 2026-11-03T18:20:24.147419Z | 10.567 | 2250 | 256 | 1 |
| E3 | 2026-11-03T18:26:10.155274Z | 10.606 | 2250 | 256 | 0 |

E2 atingiu exatamente seu teto de 256 tokens. O cliente aplicou a regra
conservadora `eval_count >= num_predict` e retornou `GENERATION_LIMIT`.
Não foi alegado truncamento comprovado: o servidor informou `stop`, e o texto
bruto retornado em E2 é idêntico ao de E3. E3 retornou 256 tokens com teto de 512,
permitindo prosseguir nas validações sem alterar essa regra.

Reservas completas de entrada + saída: E1 `1893 + 256 = 2149`,
E2 `2250 + 256 = 2506`, E3 `2250 + 512 = 2762`; todas inferiores a 4096.
O teste anterior de compatibilidade com contexto 256 e entrada sintética de
4137 tokens retornou HTTP 400 explícito. Contagem de tokens isoladamente não
prova ausência de truncamento, nem o teste de entrada excedente verifica o
esgotamento do contexto durante geração longa.

## 2. Validação estrutural

| Verificação | E1 | E2 | E3 |
|---|---|---|---|
| Conclusão aceita pelo cliente | Sim | Não: teto atingido | Sim |
| JSON da candidata e Pydantic | Passaram | Não executados | Passaram |
| Referências | `REFERENCES_IN_CONTEXT` | Não avaliadas | `REFERENCES_IN_CONTEXT` |
| `invalid_chunk_ids` | `[]` | Sem relatório estrutural | `[]` |
| Ação declarada | `ACTION_TYPE_ALLOWED` | Não avaliada | `ACTION_TYPE_ALLOWED` |
| `structural_checks_passed` | `true` | Não calculado | `true` |
| `semantic_support_status` | `not_evaluated` | `not_evaluated` | `not_evaluated` |

E2 preservou o corpo bruto, sem reparar ou validar o JSON interno e sem criar
`candidate.json`. O texto de E2 foi lido apenas para diagnóstico qualitativo.
E1 e E3 passaram nas regras de presença de referências e tipo de ação declarado;
isso não comprova suporte semântico nem autoriza execução.

### Candidata integral de E1

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

### Candidata integral de E3

O conteúdo de `message.content` em E2 e E3 é idêntico. Somente E3 chegou às
validações da candidata; não se atribui retroativamente passagem estrutural a E2.

```json
{
  "text": "Fatos observados: O incidente ocorreu no aplicativo checkout, com status de degradação e taxa de erros de 12.5%. Houve logs de erro e aviso de latência elevada. Os timeouts foram registrados em 2026-10-05T12:00:00Z e 2026-10-05T12:00:05Z. O monitoring indicou latência p95 de 1800 ms. Os dados do histórico mostram que há similaridades em problemas de timeout e latência elevada, mas não foi comprovado que a configuração seja a única causa. Verificações sugeridas: Solicitar verificação do status do serviço de pagamentos e da configuração do pool de conexões. Não há dados suficientes para concluir a causa raiz.",
  "action_type": "request_verification",
  "cited_chunk_ids": [
    "RB-001-02-01",
    "RB-001-03-02",
    "RB-001-04-02"
  ]
}
```

## 3. Avaliação humana do conteúdo

Revisão qualitativa assistida, registrada para avaliação humana. Não representa
aprovação explícita do usuário nem um avaliador semântico automático.

| Aspecto | E1 | E2 (texto bruto) e E3 |
|---|---|---|
| Fatos sustentados | Logs ERROR/WARN e métricas degradadas correspondem ao contexto. | Inclui métricas corretas: 12,5% de erros e p95 de 1800 ms. |
| Fatos sem suporte | “Dados insuficientes foram registrados” transforma uma orientação condicional de `RB-001-03-02` em acontecimento não demonstrado. | Remove essa afirmação, mas chama os dois logs de timeouts; o segundo é `Payment request exceeded latency threshold`. |
| Separação do histórico | Não sugere repetir a resolução anterior. | Mistura históricos no bloco de fatos e sugere verificar o pool de conexões com base na resolução de HIST-001, sem suporte nas orientações citadas. A ressalva sobre configuração como causa pertence ao incidente passado. |
| Condições da orientação | Investigação de pagamentos pertinente, porém genérica e sem todas as condições. | Não preserva claramente a condição de timeouts recorrentes acompanhados de degradação nem solicita explicitamente monitoring e logs de pagamentos. |
| Dados necessários ausentes | Cita ausência de logs genericamente, embora haja logs de checkout. | Não explicita que monitoring/logs de pagamentos não foram fornecidos no contexto, apesar da instrução adicional. |
| Clareza e concisão | Parágrafo único sem rótulos. | Usa os dois rótulos, mas o bloco de fatos é longo e mistura experiência passada com o incidente atual. |
| Causa raiz e execução | Não demonstra causa raiz nem solicita mudança de ambiente. | Declara que não há dados suficientes para concluir a causa raiz e mantém `request_verification`; isso não valida semanticamente o restante do texto. |

Conclusão da revisão: as instruções adicionais melhoraram a organização e
removeram uma afirmação indevida, mas não eliminaram imprecisões e extrapolações.
Aumentar o orçamento em E3 não melhorou o texto; apenas permitiu que ele fosse
avaliado abaixo do teto do cliente. As duas candidatas que passaram
estruturalmente precisam de revisão de conteúdo antes de uso como orientação
revisada. Nenhuma foi executada ou integrada à API.

## Instruções adicionais exatas de E2 e E3

As instruções oficiais do pacote não foram editadas. Em cópias temporárias do
script, a mensagem system original recebeu `"\n\n"` seguido do texto abaixo.
A mensagem user e o restante da requisição foram conferidos como idênticos;
entre E2 e E3, somente `options.num_predict` mudou de 256 para 512.
O ajuste de `NUM_PREDICT` na cópia também alimenta a barreira de limite e a
reserva de contexto existentes, sem mudar sua lógica.

```text
Produza uma candidata curta, com text, action_type e cited_chunk_ids.

No campo text, separe explicitamente “Fatos observados:” de “Verificações sugeridas:”, sem criar novos campos JSON.

Fatos observados: descreva somente informações demonstradas pelas evidências do incidente atual. Não apresente históricos como acontecimentos atuais nem orientações do runbook como atividades realizadas.

Verificações sugeridas: formule solicitações futuras de observação ou verificação, preservando as condições relevantes do runbook. Uma instrução como “se faltarem dados, registrar quais faltam” não permite afirmar que dados faltaram ou que foram registrados.

Não afirme que uma consulta, verificação, registro ou ação foi realizada sem evidência explícita de sua realização. A presença de uma orientação na documentação não constitui essa evidência.

Se uma informação necessária à verificação sugerida não estiver no contexto, diga “não fornecida no contexto”, sem concluir que ela não existe.

Use preferencialmente uma frase por parte. Preserve condições e limitações necessárias à interpretação, mesmo quando exigirem uma frase adicional.

Mantenha somente observe ou request_verification como ações permitidas. Cite exclusivamente os mesmos IDs disponíveis em documentation e document_limits, incluindo os trechos que sustentam condições ou ressalvas utilizadas. Não acrescente IDs nem use históricos como citações documentais.

Não conclua causa raiz a partir de timeout nem apresente a candidata como autorização de execução.
```

## Scripts, testes e rastreabilidade

- [Script experimental](send_package_to_ollama.py): mantém a variante E1,
  com teto 256. A CLI não tem opção para instruções adicionais ou orçamento.
- [Testes isolados](test_send_package_to_ollama.py): resultados simulados,
  sem Ollama ou rede, cobrindo conclusão, limites, contrato, referências,
  política, separação das mensagens e preservação de respostas incompletas.
- [Relatório detalhado de E1](ollama_candidate_inc001_report.md).
- E2/E3 foram executados em cópias temporárias; as diferenças necessárias estão
  registradas neste relatório, sem duplicar scripts inteiros no repositório.

Comando dos testes, a partir da raiz do projeto:

```bash
docker run --rm --network none \
  --mount type=bind,source="$PWD",target=/workspace,readonly \
  --workdir /workspace/experiments \
  ai-incident-operations-assistant-ai-app \
  python -B -m unittest -q test_send_package_to_ollama
```

Resultado na revisão final: **20 testes passaram**, sem rede ou nova geração.
A mensagem `Erro operacional: disk full` é emitida pelo teste simulado de falha
de gravação e não indica falha real do disco.

Os três diretórios originais locais, não incluídos no Git, são:

- E1: `/private/tmp/ollama-package-run.15AWw3/run/`.
- E2: `/private/tmp/ollama-instructions-comparison.9xu3Hl/run/`.
- E3: `/private/tmp/ollama-output512.StxEYv/run/`.

Contêm requisição, pacote, parâmetros, metadados, corpo HTTP e resultado;
`candidate.json` existe apenas em E1 e E3. Arquivos temporários podem desaparecer
após limpeza do sistema. Este relatório preserva as instruções, candidatas e
resultados relevantes, mas não constitui arquivo completo dos dados brutos.

## 4. Limitações conhecidas

- Uma única chamada por condição, apenas um incidente e um runbook; não há base
  para generalizar qualidade, estabilidade ou desempenho.
- Os tempos incluem carregamento e condições distintas de cache/memória;
  as diferenças observadas não demonstram aceleração causada pelas instruções.
- Temperatura zero não garante reprodutibilidade entre ambientes ou versões.
- O resultado de E2 foi rejeitado pela barreira do cliente, não por `done_reason=length`.
- O texto idêntico de E2/E3 não converte E2 em candidata validada.
- Referências presentes e ação declarada permitida não verificam se cada
  afirmação decorre dos chunks, se a condição se aplica ou se o texto contradiz
  o tipo de ação declarado.
- Separação entre instruções e evidências não comprova resistência a instruções
  maliciosas nos dados.
- `CONTEXT_READY` não implica causa raiz conhecida nem contexto completo para
  qualquer verificação futura. A ausência de dados deve ser delimitada.
- O script verifica reserva com contagens retornadas e depende do comportamento
  de contexto da versão/modelo testados; não dispõe de pré-contagem independente
  do prompt completo pelo tokenizer do servidor.
- Política oficial, API, audit, índices e configurações persistentes permaneceram
  inalterados; nenhuma ação sugerida foi executada.
