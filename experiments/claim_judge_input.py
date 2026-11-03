"""Seleção explícita da entrada cega e conferência de referências locais."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ai-app'))
from recommendation_models import RecommendationCandidate
from claim_judge_models import ClaimJudgment, JudgeInput


def build_judge_input(dataset, example):
    source_id = example['source_run_id']
    source = dataset['source_runs'][source_id]
    if example['model'] != source['model'] or example['audit_event_id'] != source['audit_event_id']:
        raise ValueError('Rastreabilidade incompatível com source_run_id')
    if example['candidate_reference'] != f'#/source_runs/{source_id}/candidate':
        raise ValueError('Referência à candidata incompatível')
    candidate = RecommendationCandidate.model_validate(source['candidate'], strict=True)
    span = example['candidate_text_span']
    if type(span['start']) is not int or type(span['end']) is not int:
        raise ValueError('Posições do fragmento devem ser inteiros')
    if not 0 <= span['start'] < span['end'] <= len(candidate.text):
        raise ValueError('Posições do fragmento inválidas')
    if candidate.text[span['start']:span['end']] != example['statement_fragment']:
        raise ValueError('Fragmento não corresponde à candidata')
    if example['candidate_cited_chunk_ids'] != candidate.cited_chunk_ids:
        raise ValueError('Citações globais incompatíveis')
    # Nenhum campo é copiado integralmente do exemplo: exclui human_review,
    # citation_review, observation e a reformulação humana da sugestão.
    evidence = []
    for item in example['available_evidence']:
        has_value, has_excerpt = 'value' in item, 'excerpt' in item
        if has_value == has_excerpt:
            raise ValueError('Cada evidência deve fornecer value ou excerpt, sem ambiguidade')
        evidence.append({
            'source_type': item['source_type'], 'source_id': item['source_id'],
            'value': item['value'] if has_value else item['excerpt'],
        })
    return JudgeInput.model_validate({
        'example_id': example['example_id'], 'source_run_id': source_id,
        'source_model': source['model'], 'audit_event_id': source['audit_event_id'],
        'statement_fragment': example['statement_fragment'],
        'statement_type': example['statement_interpretation']['type'],
        'candidate_text_span': {'start': span['start'], 'end': span['end']},
        'candidate_context': candidate.model_dump(),
        'candidate_cited_chunk_ids': candidate.cited_chunk_ids,
        'evidence_scope': 'selected_evidence_only_not_complete_context',
        'evidence': evidence,
    }, strict=True)


def validate_judgment(payload, sent_input):
    """Pointer é relativo ao JSON decodificado da mensagem user enviada.

    Só evidence é citável. Nem a candidata, nem metadados ou fontes originais
    não enviadas podem fundamentar o julgamento por referência.
    """
    judgment = ClaimJudgment.model_validate(payload, strict=True)
    if judgment.example_id != sent_input['example_id']:
        raise ValueError('example_id difere da entrada enviada')
    if judgment.statement_type != sent_input['statement_type']:
        raise ValueError('statement_type difere da entrada enviada')
    for reference in judgment.evidence_references:
        match = re.fullmatch(r'/evidence/(0|[1-9][0-9]*)/value(?:/.*)?', reference.json_pointer)
        if not match:
            raise ValueError('Pointer deve apontar para value de uma evidência enviada')
        index = int(match.group(1))
        try:
            item = sent_input['evidence'][index]
        except (IndexError, KeyError):
            raise ValueError('Evidência referenciada não foi enviada') from None
        if item['source_id'] != reference.source_id:
            raise ValueError('source_id não corresponde à evidência no pointer')
        node = sent_input
        for part in reference.json_pointer[1:].split('/'):
            if re.search(r'~(?![01])', part):
                raise ValueError('Escape inválido em JSON pointer')
            part = part.replace('~1', '/').replace('~0', '~')
            try:
                if isinstance(node, list):
                    if not re.fullmatch(r'0|[1-9][0-9]*', part):
                        raise ValueError('Índice inválido')
                    node = node[int(part)]
                elif isinstance(node, dict):
                    node = node[part]
                else:
                    raise ValueError('Pointer avança além de um valor escalar')
            except (IndexError, KeyError):
                raise ValueError('Pointer não existe na entrada enviada') from None
    return judgment
