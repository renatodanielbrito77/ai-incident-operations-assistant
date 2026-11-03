# Experimento: julgamento semântico de três afirmações

Data: 2026-11-03. Registro retrospectivo de uma chamada por exemplo, sem novas
chamadas ou reparação de respostas para produzir este relatório.

## Objetivo, entrada e parâmetros

Avaliar três afirmações de [claim_examples.json](../evals/claim_examples.json),
provenientes da candidata de INC-001 da execução E3, distinguindo a validade do
contrato da resposta, a concordância com a revisão humana e a qualidade da
justificativa. O resultado não aprova candidatas nem autoriza ações.

- `source_run_id=E3`; `audit_event_id=afc36a70-04a9-4039-9631-d8820c2f115c`.
- Modelo local `qwen3:1.7b`; contexto `4096`; saída máxima `512` tokens;
  temperatura `0`; timeout total de `120` segundos; `keep_alive=0`.
- `truncate=false`, `shift=false`, `think=false`, `stream=false`.
- Endpoint usado pelo container: `http://host.docker.internal:11434/api/chat`.
- Mesmo schema Pydantic `ClaimJudgment` para cada chamada independente.
- Sem retries, correção de JSON, aumento automático de limites ou nova busca.

A entrada foi montada por seleção explícita de campos. `human_review`,
`citation_review`, observações e reformulações humanas ficaram fora das mensagens.
O tipo da afirmação foi fornecido como metadado, não julgado pelo modelo.
A candidata completa forneceu contexto gramatical, com instrução explícita de
que não poderia servir como evidência de si mesma.

Foram enviados somente os valores e recortes de `available_evidence` dos exemplos,
não o pacote original completo. Os pointers originais dos exemplos foram
substituídos por referências ao objeto JSON realmente enviado na mensagem user.
A validação aceita referências apenas em `/evidence/<índice>/value`, ou seus
subcampos existentes, conferindo o `source_id` no mesmo registro. Referências à
candidata, metadados ou artefatos não enviados são rejeitadas.

## Conclusão das gerações

As três chamadas retornaram HTTP 200, `done=true`, `done_reason="stop"`, sem
thinking retornado e abaixo do teto de 512 tokens. Isso não equivale a três
julgamentos válidos.

| Exemplo | Conclusão UTC | Tempo do cliente (s) | Tokens entrada / saída |
|---|---|---:|---:|
| CLAIM-001 | 2026-11-03T19:00:46.873981Z | 6.971 | 993 / 158 |
| CLAIM-002 | 2026-11-03T19:00:54.713953Z | 7.825 | 1054 / 248 |
| CLAIM-003 | 2026-11-03T19:01:00.319179Z | 5.578 | 1002 / 181 |

## Resultado consolidado

**Duas saídas válidas: uma concordância e uma divergência. Além delas, uma saída
foi rejeitada pelo contrato.** Não houve abstenção válida. Não é apresentada uma
taxa geral de qualidade, acurácia ou aprovação.

| Exemplo | Validade da saída | Rótulo do modelo | Rótulo humano usado na comparação | Resultado |
|---|---|---|---|---|
| CLAIM-001 | Válida | `sustentado` | `sustentado` | Concordância |
| CLAIM-002 | Válida | `sustentado` | `impreciso` | Divergência |
| CLAIM-003 | Inválida | Combinação incompatível: `abstained` e classificação preenchida | Não consultado para comparação deste resultado | Saída rejeitada |

A comparação foi executada somente após validar a conclusão, o JSON, o contrato,
a identidade do exemplo/tipo e as referências à entrada efetivamente enviada.
As anotações humanas originais não foram alteradas.

Código de saída do conjunto: `1`, devido à saída rejeitada, não à divergência de
CLAIM-002. Uma divergência de um julgamento válido é registrada separadamente,
sem ser confundida com erro operacional ou de contrato.

## Concordância: CLAIM-001

Julgamento integral validado:

```json
{
  "example_id": "CLAIM-001",
  "statement_type": "current_fact",
  "assessment_status": "evaluated",
  "classification": "sustentado",
  "reason": "A evidência de monitoring (source_id: INC-001) confirma o valor de 1800.0 ms para a latência p95, o que sustenta a afirmação atual. A referência citada é válida e está presente no contexto da mensagem user, conforme especificado na evidence_scope.",
  "evidence_references": [
    {
      "source_id": "INC-001",
      "json_pointer": "/evidence/0/value"
    }
  ]
}
```

O valor atual de latência sustenta o fragmento analisado. A referência resolve
para `1800.0` na entrada enviada e corresponde ao `source_id=INC-001`.
A concordância diz respeito a este exemplo, não comprova a confiabilidade geral
do avaliador. A presença da referência na entrada também não transforma a métrica
em chunk documental citado pela candidata.

## Divergência: CLAIM-002

Julgamento integral validado:

```json
{
  "example_id": "CLAIM-002",
  "statement_type": "suggestion",
  "assessment_status": "evaluated",
  "classification": "sustentado",
  "reason": "A sugestão 'Solicitar verificação do status do serviço de pagamentos' é sustentada pela evidência fornecida. A evidência inclui a recomendação do runbook (RB-001-04-02) e o log de timeout (INC-001), que corroboram a necessidade de verificação do serviço de pagamentos e da configuração do pool de conexões. A falta de dados suficientes para concluir a causa raiz é mencionada, mas a sugestão é baseada em evidências disponíveis e relevantes.",
  "evidence_references": [
    {
      "source_id": "RB-001-04-02",
      "json_pointer": "/evidence/0/value"
    },
    {
      "source_id": "INC-001",
      "json_pointer": "/evidence/1/value"
    }
  ]
}
```

Os dois pointers existem e seus source_ids correspondem às evidências enviadas;
por isso a resposta é formalmente válida. A revisão humana classificou a sugestão
como `impreciso`, pois a orientação exige recorrência e a formulação não preserva
claramente as condições relevantes.

O julgamento do modelo não enfrenta essa condição. Além disso, menciona a
configuração do pool de conexões, que não pertence ao fragmento julgado nem aos
recortes de evidência desse exemplo. Também usa a ressalva sobre causa raiz que
aparece na candidata completa, não nos recortes enviados neste caso. Isso sugere
uso indevido do contexto gramatical ou extrapolação, apesar das instruções.
A validade dos pointers não demonstra que a justificativa decorre dos valores
apontados. O resultado não foi promovido a aprovação automática.

## Saída inválida: CLAIM-003

Conteúdo bruto integral retornado pelo modelo, preservado sem reparação:

```json
{
  "example_id": "CLAIM-003",
  "statement_type": "suggestion",
  "assessment_status": "abstained",
  "classification": "não sustentado",
  "reason": "A evidência apresenta apenas um fragmento histórico (HIST-001) indicando que uma alteração no pool de conexões foi reverteida, mas não há dados suficientes para concluir que essa alteração seja a causa da situação atual. A sugestão de verificar o status do serviço de pagamentos e a configuração do pool de conexões não é fundamentada por evidências completas ou diretas.",
  "evidence_references": [
    {
      "source_id": "HIST-001",
      "json_pointer": "/evidence/0/value"
    }
  ]
}
```

O contrato exige `classification=null` quando `assessment_status="abstained"`.
O modelo preencheu uma classificação, tornando a combinação inválida.
Não foi criado `judgment.json` ou `comparison.json` para esse caso. A resposta
não foi contabilizada como concordância, divergência ou abstenção válida e não
houve nova tentativa para substituí-la.

## Implementação e verificação

Arquivos experimentais:

- [Modelos](claim_judge_models.py): entrada e julgamento estritos, sem campos extras,
  classificação coerente com o status e possibilidade de abstenção.
- [Montagem e referências](claim_judge_input.py): seleção da entrada sem anotações
  humanas e conferência de pointers/source_id contra a mensagem efetivamente enviada.
- [Executor](judge_claim_examples.py): uma chamada por exemplo, preservação de
  artefatos e comparação humana somente após saída válida.
- [Testes](test_judge_claim_examples.py): 21 testes novos; reutiliza o transporte
  experimental existente, também verificado com seus 20 testes.

Comando executado no container com o projeto montado somente para leitura:

```bash
docker run --rm --network none \
  --mount type=bind,source="$PWD",target=/workspace,readonly \
  --workdir /workspace/experiments \
  ai-incident-operations-assistant-ai-app \
  python -B -m unittest -q test_judge_claim_examples test_send_package_to_ollama
```

Resultado: **41 testes passaram** antes das chamadas reais. A mensagem
`Erro operacional: disk full` pertence ao teste simulado de falha de gravação;
não é uma falha real do disco. Os testes não geram julgamentos semânticos reais.

As mensagens efetivamente enviadas foram conferidas sem `human_review`,
`citation_review` ou `observation`. Alterar essas anotações nos testes não altera
a requisição. As verificações também cobrem pointers existentes em outro artefato,
source_id incorreto, referências à própria candidata, JSON inválido, limites,
conclusão incompleta e abstenção, separando os tipos de resultado.

## Artefatos e limitações

Artefatos originais locais, fora do Git:
`/private/tmp/claim-judge-run.iezeRD/run/`.
O diretório contém parâmetros, cópia do conjunto, resumo e um subdiretório por
exemplo com entrada enviada, requisição, hashes, corpo HTTP bruto, metadados e
resultado. `judgment.json` e `comparison.json` existem apenas para CLAIM-001 e
CLAIM-002. Esses caminhos temporários podem deixar de existir após limpeza do
sistema; os três conteúdos retornados estão transcritos neste relatório.

- Apenas três exemplos e uma chamada por exemplo; não há base para uma taxa geral
  de qualidade ou para generalizar confiabilidade.
- Os recortes foram selecionados na elaboração humana dos exemplos. Ocultar os
  rótulos evita seu envio direto, mas não elimina esse viés de seleção.
- O contexto completo da candidata pode influenciar o modelo, mesmo quando é
  explicitamente proibido usá-lo como evidência. A justificativa de CLAIM-002
  demonstra que essa separação não é garantia semântica.
- A conferência de source_id e pointer garante identidade e existência da
  referência na entrada, não que ela sustente a conclusão ou a justificativa.
- Abstenção é permitida, mas a tentativa de CLAIM-003 violou o contrato; não foi
  demonstrada uma abstenção válida nas chamadas reais desta execução.
- Os exemplos atuais contêm um fato atual e duas sugestões; a categoria
  `historical_fact` está no contrato, mas não foi exercitada por chamada real.
- JSON schema, Pydantic e instruções não substituem a revisão humana do conteúdo.
  A comparação usa os rótulos existentes como referência, sem afirmar que são
  verdade absoluta ou fazer revisão automática desses rótulos.
- Não há validação de resistência a instruções maliciosas, estabilidade entre
  execuções ou reprodutibilidade garantida por temperatura zero.
- Esta avaliação experimental não sobrescreve `automated_semantic_support_status`
  das anotações nem o status dos validadores existentes. Não integra API ou audit,
  não executa ações e não cria aprovação automática.
