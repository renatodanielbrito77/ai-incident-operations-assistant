# Experimento: conteúdo versus títulos e conteúdo

Data: 2026-11-02.

## Hipótese, variantes e parâmetros

Acrescentar seção e subseção ao texto do embedding poderia melhorar a recuperação
dos trechos esperados, especialmente nas consultas vagas e sobre restrições.

- **A:** somente `content`.
- **C:** títulos presentes, sem abreviações, unidos por ` | `, seguidos de duas
  quebras de linha e do conteúdo completo.
- Ambas usam os mesmos 11 trechos e o modelo
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, em CPU.
- Mesmos vetores de consulta, distância cosseno, `top_k=3` e limiar `0.50`.
- Seis casos oficiais, RET-001 a RET-006, com expectativas inalteradas.

Scripts: [contagem de tokens](count_chunk_variant_tokens.py) e
[comparação dos embeddings](compare_chunk_embeddings.py).

## Divisão experimental e validações

O chunk `RB-001-03-01` foi dividido antes do item 4 da lista:

| Derivado | Conteúdo | Tokens A | Tokens C |
|---|---|---:|---:|
| `RB-001-03-01-part-01` | Introdução e itens 1–3 | 71 | 79 |
| `RB-001-03-01-part-02` | Itens 4–6 | 54 | 62 |

Ambos preservam `parent_chunk_id="RB-001-03-01"`, ordem por `part_index`, origem,
documento, seção e subseção. A concatenação dos conteúdos reconstrói exatamente o
texto original. Os nove demais chunks foram preservados. IDs únicos e limite de
128 tokens foram validados, sem truncamento e incluindo os títulos de C e os
tokens especiais, antes de gerar embeddings.

A expectativa pelo ID pai só é satisfeita quando **os dois derivados** aparecem.
Um único derivado não equivale ao chunk completo. Os casos oficiais não foram
reescritos; essa equivalência existe apenas no avaliador experimental.

## Resultados

Busca vetorial e contexto documental final foram avaliados separadamente. O
contexto final acrescenta os Limites dos documentos recuperados por filtro, sem
atribuir pontuação a esses trechos.

| Caso | Busca A | Busca C | Contexto A | Contexto C |
|---|---|---|---|---|
| RET-001 | Aprovado | Aprovado | Aprovado | Aprovado |
| RET-002 | Aprovado | Aprovado | Aprovado | Aprovado |
| RET-003 | Aprovado | Aprovado | Aprovado | Aprovado |
| RET-004 | Reprovado | Reprovado | Reprovado | Reprovado |
| RET-005 | Reprovado | Reprovado | Aprovado | Aprovado |
| RET-006 | Aprovado | Aprovado | Aprovado | Aprovado |

Ambas as variantes aprovaram **4/6 na busca** e **5/6 no contexto documental
final**, sem erros operacionais. Código de saída do experimento: `1`, por
expectativas reprovadas.

RET-004 não recuperou resultados em nenhuma variante. Em RET-005, somente
`part-01` apareceu, na segunda posição: `0.567729` em A e `0.524501` em C. Isso
não satisfez a regra dos dois derivados. O contexto final passou porque
`RB-001-05` entrou pela consulta de Limites, sem pontuação.

As coleções experimentais foram criadas com nomes únicos e permanecem disponíveis:

```text
experiment_chunks_4b182e19d7eb4935a6d89d1d37577924_a
experiment_chunks_4b182e19d7eb4935a6d89d1d37577924_c
```

Nenhuma coleção preexistente foi excluída ou substituída. O índice, os casos e os
scripts oficiais não foram alterados.

## Decisão e limitações

**Manter o índice oficial `runbook_chunks`.** A variante C não melhorou a
quantidade de aprovações neste experimento; não há evidência suficiente para
promover uma mudança na representação oficial.

A avaliação contém apenas **seis casos e um runbook**. A e C compartilham a
divisão experimental em 11 trechos; portanto, A não é uma reprodução estrutural
do índice oficial de dez chunks. A comparação isola a inclusão de títulos entre
A e C, mas não demonstra melhoria geral nem mede isoladamente o efeito da divisão
em relação ao índice oficial.
