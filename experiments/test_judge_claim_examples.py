"""Testes experimentais sem rede, geração ou julgamento semântico real."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pydantic import ValidationError
from claim_judge_input import build_judge_input, validate_judgment
from claim_judge_models import ClaimJudgment
import judge_claim_examples as experiment
from send_package_to_ollama import HTTPResult

ROOT = Path(__file__).resolve().parents[1]


class ClaimJudgeTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'evals/claim_examples.json').read_text())
        self.example = self.data['examples'][0]
        self.input = build_judge_input(self.data, self.example).model_dump()
        self.payload = {
            'example_id': 'CLAIM-001', 'statement_type': 'current_fact',
            'assessment_status': 'evaluated', 'classification': 'sustentado',
            'reason': 'Justificativa simulada.',
            'evidence_references': [{'source_id': 'INC-001', 'json_pointer': '/evidence/0/value'}],
        }
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cases = self.root / 'cases.json'
        self.cases.write_text(json.dumps(self.data))
        self.out = self.root / 'new'

    def response(self, payload=None, **changes):
        body = {
            'message': {'role': 'assistant', 'content': json.dumps(self.payload if payload is None else payload)},
            'done': True, 'done_reason': 'stop', 'prompt_eval_count': 1200, 'eval_count': 90,
        }
        body.update(changes)
        return HTTPResult(200, [('Content-Type', 'application/json')], json.dumps(body).encode(), 1.25)

    def all_responses(self, abstain=False):
        responses = []
        for example in self.data['examples']:
            value = deepcopy(self.payload)
            value.update(example_id=example['example_id'], statement_type=example['statement_interpretation']['type'])
            value['evidence_references'][0]['source_id'] = example['available_evidence'][0]['source_id']
            if abstain:
                value.update(assessment_status='abstained', classification=None, reason='Evidência insuficiente para julgar.', evidence_references=[])
            responses.append(self.response(value))
        return responses

    def run_suite(self, transport):
        with redirect_stdout(io.StringIO()):
            return experiment.run_suite(self.cases, self.out, transport=transport)

    def test_whitelist_hides_all_human_annotations(self):
        original = deepcopy(self.data)
        before = [experiment.request_for(build_judge_input(self.data, e).model_dump()) for e in self.data['examples']]
        for example in self.data['examples']:
            example['human_review'] = {'classification': 'SEGREDO_ROTULO', 'reason': 'SEGREDO_RAZAO'}
            example['citation_review'] = {'reason': 'SEGREDO_CITACAO'}
            example['statement_interpretation']['text'] = 'SEGREDO_PARAFRASE'
            example['statement_context'] = 'SEGREDO_CONTEXTO_HUMANO'
            for evidence in example['available_evidence']:
                evidence['observation'] = 'SEGREDO_OBSERVACAO'
        after = [experiment.request_for(build_judge_input(self.data, e).model_dump()) for e in self.data['examples']]
        self.assertEqual(before, after)
        self.assertNotIn('SEGREDO', json.dumps(after))
        self.assertNotEqual(original, self.data)

    def test_original_inputs_not_mutated_and_fragments_exact(self):
        before = deepcopy(self.data)
        for example in self.data['examples']:
            sent = build_judge_input(self.data, example).model_dump()
            self.assertEqual(sent['statement_fragment'], example['statement_fragment'])
            self.assertEqual(sent['candidate_context'], self.data['source_runs']['E3']['candidate'])
            self.assertEqual(sent['candidate_cited_chunk_ids'], example['candidate_cited_chunk_ids'])
            self.assertEqual(sent['statement_type'], example['statement_interpretation']['type'])
            self.assertNotIn('statement_interpretation', sent)
            self.assertNotIn('human_review', sent)
        self.assertEqual(self.data, before)

    def test_fixed_request_parameters_and_self_evidence_warning(self):
        request = experiment.request_for(self.input)
        self.assertEqual(request['model'], 'qwen3:1.7b')
        self.assertEqual(request['options'], {'num_ctx': 4096, 'num_predict': 512, 'temperature': 0})
        for flag in ('truncate', 'shift', 'think', 'stream'):
            self.assertIs(request[flag], False)
        self.assertEqual(request['format'], ClaimJudgment.model_json_schema())
        self.assertIn('NÃO é evidência de si mesma', request['messages'][0]['content'])
        self.assertEqual(json.loads(request['messages'][1]['content']), self.input)
        self.assertIn('não o contexto original completo', request['messages'][0]['content'])

    def test_valid_reference_checks_source_with_pointer(self):
        judgment = validate_judgment(self.payload, self.input)
        self.assertEqual(judgment.classification, 'sustentado')
        changed = deepcopy(self.payload)
        changed['evidence_references'][0]['source_id'] = 'RB-001-02-01'
        with self.assertRaises(ValueError):
            validate_judgment(changed, self.input)

    def test_original_artifact_pointer_does_not_count_as_sent_evidence(self):
        for pointer in ('/evidence/monitoring/latency_p95_ms', '/evidence/99/value', '/candidate_context/text', '/candidate_cited_chunk_ids/0', '/audit_event_id', '/instructions', '/evidence/0/source_id', '#/evidence/0/value'):
            with self.subTest(pointer=pointer):
                payload = deepcopy(self.payload)
                payload['evidence_references'][0]['json_pointer'] = pointer
                with self.assertRaises(ValueError):
                    validate_judgment(payload, self.input)

    def test_pointer_is_bound_to_its_evidence_record(self):
        sent = build_judge_input(self.data, self.data['examples'][1]).model_dump()
        payload = deepcopy(self.payload)
        payload.update(example_id='CLAIM-002', statement_type='suggestion')
        payload['evidence_references'] = [{'source_id': 'INC-001', 'json_pointer': '/evidence/0/value'}]
        with self.assertRaises(ValueError):
            validate_judgment(payload, sent)
        payload['evidence_references'][0]['json_pointer'] = '/evidence/1/value'
        validate_judgment(payload, sent)

    def test_pointer_resolves_nested_value_and_rejects_malformed_paths(self):
        sent = deepcopy(self.input)
        sent['evidence'][0]['value'] = {'a/b': ['ok'], 'x~y': 1}
        for pointer in ('/evidence/0/value/a~1b/0', '/evidence/0/value/x~0y'):
            payload = deepcopy(self.payload)
            payload['evidence_references'][0]['json_pointer'] = pointer
            validate_judgment(payload, sent)
        for pointer in ('/evidence/0/value/missing', '/evidence/0/value/a~1b/01', '/evidence/0/value/a~1b/-1', '/evidence/0/value/a~2b', '/evidence/00/value'):
            payload = deepcopy(self.payload)
            payload['evidence_references'][0]['json_pointer'] = pointer
            with self.subTest(pointer=pointer), self.assertRaises(ValueError):
                validate_judgment(payload, sent)

    def test_wrong_id_or_type_rejected(self):
        for change in ({'example_id': 'CLAIM-002'}, {'statement_type': 'suggestion'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_judgment({**self.payload, **change}, self.input)

    def test_pydantic_required_strict_codes_and_no_extras(self):
        for field in self.payload:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                ClaimJudgment.model_validate({k: v for k, v in self.payload.items() if k != field}, strict=True)
        for change in ({'example_id': 1}, {'reason': '  '}, {'classification': 'approved'}, {'assessment_status': 'safe'}, {'extra': True}, {'classification': None}, {'evidence_references': []}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ClaimJudgment.model_validate({**self.payload, **change}, strict=True)

    def test_abstention_distinct_from_unsupported_and_requires_null(self):
        payload = {**self.payload, 'assessment_status': 'abstained', 'classification': None, 'evidence_references': []}
        self.assertEqual(validate_judgment(payload, self.input).assessment_status, 'abstained')
        with self.assertRaises(ValidationError):
            validate_judgment({**payload, 'classification': 'não sustentado'}, self.input)
        unsupported = validate_judgment({**self.payload, 'classification': 'não sustentado'}, self.input)
        self.assertEqual(unsupported.assessment_status, 'evaluated')

    def test_bad_fragments_sources_and_global_citations_fail_input(self):
        for field, value in (('statement_fragment', 'inventado'), ('audit_event_id', 'outro'), ('model', 'outro'), ('candidate_reference', '#/wrong'), ('candidate_cited_chunk_ids', [])):
            changed = deepcopy(self.example)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_judge_input(self.data, changed)

    def test_three_calls_preserve_exact_input_raw_response_and_compare_after_validation(self):
        responses = self.all_responses()
        transport = Mock(side_effect=responses)
        with patch.object(experiment, 'compare_with_human', wraps=experiment.compare_with_human) as compare:
            summary, code = self.run_suite(transport)
            self.assertEqual(compare.call_count, 3)
        self.assertEqual(transport.call_count, 3)
        self.assertEqual(code, 0)
        self.assertEqual(summary['validated_outputs'], 3)
        self.assertEqual(summary['agreements'], 1)
        self.assertEqual(summary['disagreements'], 2)
        self.assertEqual((self.out / 'cases_snapshot.json').read_bytes(), self.cases.read_bytes())
        for call, example, response in zip(transport.call_args_list, self.data['examples'], responses):
            directory = self.out / example['example_id']
            request = json.loads(call.args[1])
            self.assertEqual(request, json.loads((directory / 'request.json').read_bytes()))
            self.assertEqual(json.loads(request['messages'][1]['content']), json.loads((directory / 'input.json').read_text()))
            self.assertEqual((directory / 'response.body').read_bytes(), response.body)
            self.assertEqual(call.args[2], 120)
            self.assertTrue((directory / 'judgment.json').exists())
            self.assertTrue((directory / 'comparison.json').exists())

    def test_invalid_outputs_never_access_human_labels_or_compare(self):
        transport = Mock(return_value=self.response({**self.payload, 'evidence_references': [{'source_id': 'INC-001', 'json_pointer': '/candidate_context/text'}]}))
        for example in self.data['examples']:
            del example['human_review']
        self.cases.write_text(json.dumps(self.data))
        with patch.object(experiment, 'compare_with_human') as compare:
            summary, code = self.run_suite(transport)
            compare.assert_not_called()
        self.assertEqual(transport.call_count, 3)
        self.assertEqual(summary['validated_outputs'], 0)
        self.assertEqual(code, 1)
        self.assertFalse(any(self.out.rglob('comparison.json')))

    def test_abstentions_are_not_mislabeled_as_errors_or_disagreements(self):
        summary, code = self.run_suite(Mock(side_effect=self.all_responses(abstain=True)))
        self.assertEqual(code, 0)
        self.assertEqual(summary['abstentions'], 3)
        self.assertEqual(summary['disagreements'], 0)
        self.assertEqual(summary['errors_or_rejected_outputs'], 0)

    def test_limit_incomplete_and_thinking_never_produce_judgment(self):
        for changes in ({'eval_count': 512}, {'done_reason': 'length'}, {'done': False}, {'message': {'role': 'assistant', 'content': '{}', 'thinking': 'unexpected'}}):
            result, code = experiment.inspect_response(self.response(**changes), self.input)
            with self.subTest(changes=changes):
                self.assertEqual(code, 1)
                self.assertNotIn('judgment', result)

    def test_invalid_json_and_contract_are_not_repaired(self):
        for content in ('```json\n{}\n```', '{"partial":', '{}', 'NaN', '{"a":1,"a":2}'):
            result, code = experiment.inspect_response(self.response(message={'role': 'assistant', 'content': content}), self.input)
            self.assertEqual(code, 1)
            self.assertNotIn('judgment', result)

    def test_timeout_and_http_error_remain_operational_not_abstention(self):
        for response in (HTTPResult(None, [], b'partial', 120, 'TimeoutError'), HTTPResult(400, [], b'{"error":"context exceeded"}', 1), HTTPResult(200, [], b'bad envelope', 1)):
            result, code = experiment.inspect_response(response, self.input)
            self.assertEqual(code, 2)
            self.assertEqual(result['status'], 'operational_error')
            self.assertNotIn('judgment', result)

    def test_insufficient_context_reserve_or_bad_metrics_stop(self):
        for change in ({'prompt_eval_count': 4000}, {'prompt_eval_count': True}, {'eval_count': None}):
            result, code = experiment.inspect_response(self.response(**change), self.input)
            self.assertEqual(code, 2)
            self.assertNotIn('judgment', result)

    def test_global_errors_make_zero_calls(self):
        for index, text in enumerate(('bad json', json.dumps({**self.data, 'examples': [self.example] * 3}))):
            self.cases.write_text(text)
            transport = Mock()
            with redirect_stdout(io.StringIO()):
                summary, code = experiment.run_suite(self.cases, self.root / f'global-{index}', transport=transport)
            transport.assert_not_called()
            self.assertEqual(code, 2)
            self.assertEqual(summary['status'], 'global_error')

    def test_case_input_error_does_not_prevent_other_single_calls(self):
        self.data['examples'][0]['statement_fragment'] = 'invalid'
        self.cases.write_text(json.dumps(self.data))
        responses = self.all_responses()[1:]
        transport = Mock(side_effect=responses)
        summary, code = self.run_suite(transport)
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(code, 2)
        self.assertEqual(summary['validated_outputs'], 2)

    def test_existing_directory_is_never_overwritten(self):
        self.out.mkdir()
        transport = Mock()
        with self.assertRaises(FileExistsError):
            self.run_suite(transport)
        transport.assert_not_called()


if __name__ == '__main__':
    unittest.main()
