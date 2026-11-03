"""Orquestração isolada: HTTP simulado, sem serviços, embeddings ou audit real."""

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ai-app'))
import test_llm_input_package as fixtures
from send_package_to_ollama import HTTPResult
import investigate_and_report as flow


class InvestigationFlowTest(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.LLMInputPackageTest()
        fixture.setUp()
        self.context = fixture.context
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.counter = 0
        self.candidate = {
            'text': 'Solicitar verificação do monitoring e dos logs de pagamentos.',
            'action_type': 'request_verification', 'cited_chunk_ids': ['RB-001-04-02'],
        }
        # Qualquer caminho que esqueça a injeção falha, sem tocar na rede.
        block = patch.object(flow.generation, 'post_once', side_effect=AssertionError('Rede proibida no teste'))
        block.start()
        self.addCleanup(block.stop)

    def response(self, body, status=200, error=None):
        return HTTPResult(status, [('Content-Type', 'application/json')],
                          body if isinstance(body, bytes) else json.dumps(body).encode(), 0.5, error)

    def generated_response(self, candidate=None, **changes):
        body = {
            'model': 'qwen3:1.7b', 'done': True, 'done_reason': 'stop',
            'prompt_eval_count': 1800, 'eval_count': 90,
            'message': {'role': 'assistant', 'content': json.dumps(self.candidate if candidate is None else candidate)},
        }
        body.update(changes)
        return self.response(body)

    def run_flow(self, investigation=None, generated=None, **kwargs):
        self.counter += 1
        out = self.root / f'run-{self.counter}'
        api = Mock(return_value=self.response(self.context) if investigation is None else investigation)
        ollama = Mock(return_value=self.generated_response() if generated is None else generated)
        result, code = flow.run_flow('INC-001', out, investigation_transport=api, generation_transport=ollama, **kwargs)
        return result, code, out, api, ollama

    def p1(self):
        return {
            'audit_event_id': 'p1-original-id', 'incident': {**self.context['incident'], 'priority': 'P1'},
            'status': 'manual_escalation_required', 'reason': 'Tratamento humano obrigatório.',
        }

    def missing_logs(self):
        return {
            'audit_event_id': 'logs-original-id', 'incident': self.context['incident'],
            'status': 'additional_data_required', 'analysis_code': 'NO_LOG_MESSAGE',
            'reason': 'Sem mensagem.', 'requested_data': ['Enviar logs.'],
        }

    def test_success_reuses_components_preserves_context_ids_and_parameters(self):
        with patch.object(flow, 'build_llm_input_package', wraps=flow.build_llm_input_package) as build, \
             patch.object(flow.generation, 'run_experiment', wraps=flow.generation.run_experiment) as generate, \
             patch.object(flow, 'render_candidate_report', wraps=flow.render_candidate_report) as render:
            result, code, out, api, ollama = self.run_flow()
        build.assert_called_once()
        generate.assert_called_once()
        render.assert_called_once()
        self.assertEqual(code, 0)
        self.assertEqual(result['final_state'], 'STRUCTURAL_CHECKS_PASSED')
        self.assertTrue(result['candidate_produced'])
        self.assertEqual(result['audit_event_id'], self.context['audit_event_id'])
        self.assertEqual(result['semantic_support_status'], 'not_evaluated')
        api.assert_called_once()
        ollama.assert_called_once()
        self.assertEqual(api.call_args.args[0], 'http://127.0.0.1:8000/investigate/INC-001')
        self.assertEqual(api.call_args.args[2], 30)
        request = json.loads(ollama.call_args.args[1])
        self.assertEqual(request['model'], 'qwen3:1.7b')
        self.assertEqual(request['options'], {'num_ctx': 4096, 'num_predict': 256, 'temperature': 0})
        for flag in ('truncate', 'shift', 'think', 'stream'):
            self.assertIs(request[flag], False)
        self.assertEqual(ollama.call_args.args[2], 120)
        package = json.loads((out / 'package.json').read_text())
        self.assertEqual(json.loads(request['messages'][0]['content']), package['instructions'])
        from llm_input_models import DIRECTIVES
        self.assertEqual(package['instructions']['directives'], list(DIRECTIVES))
        self.assertEqual(package['evidence'], json.loads((out / 'generation/package.json').read_text())['evidence'])
        self.assertEqual((out / 'investigation/response.body').read_bytes(), self.response(self.context).body)
        self.assertEqual((out / 'generation/response.body').read_bytes(), self.generated_response().body)
        report = (out / 'report.md').read_text()
        self.assertIn('Candidata para revisão humana', report)
        self.assertIn('Sustentação semântica não avaliada', report)
        self.assertIn(self.context['audit_event_id'], report)
        self.assertEqual(json.loads((out / 'parameters.json').read_text())['policy_version'], '1.0')

    def test_p1_and_missing_logs_never_generate_or_render_candidate(self):
        for body, reason in ((self.p1(), 'P1'), (self.missing_logs(), 'NO_LOG_MESSAGE')):
            with self.subTest(reason=reason), patch.object(flow, 'render_candidate_report') as render, \
                 patch.object(flow.generation, 'run_experiment') as generate:
                result, code, out, api, ollama = self.run_flow(investigation=self.response(body))
                self.assertEqual((code, result['final_state']), (0, 'NOT_ELIGIBLE'))
                self.assertEqual(result['reason_code'], reason)
                self.assertEqual(result['audit_event_id'], body['audit_event_id'])
                self.assertFalse(result['generation_attempted'])
                self.assertFalse(result['candidate_produced'])
                generate.assert_not_called()
                ollama.assert_not_called()
                render.assert_not_called()
                self.assertFalse((out / 'package.json').exists())
                self.assertFalse((out / 'generation').exists())
                self.assertIn('Resumo da execução', (out / 'report.md').read_text())
                self.assertIn('Código 0 não significa candidata produzida', (out / 'report.md').read_text())

    def test_both_abstentions_are_normal_without_llm(self):
        for analysis in ('NO_DOCUMENTATION', 'MISSING_DOCUMENT_LIMITS'):
            context = deepcopy(self.context)
            context.update(analysis_code=analysis, analysis_status='abstained', document_limits=[])
            if analysis == 'NO_DOCUMENTATION':
                context.update(documentation=[], documentation_status='no_matches')
            with self.subTest(analysis=analysis), patch.object(flow, 'render_candidate_report') as render:
                result, code, out, api, ollama = self.run_flow(investigation=self.response(context))
                self.assertEqual((code, result['final_state'], result['reason_code']), (0, 'NOT_ELIGIBLE', 'ABSTAINED'))
                ollama.assert_not_called()
                render.assert_not_called()

    def test_http_errors_are_investigation_failure_not_inelegibility(self):
        for status in (404, 503, 504):
            response = self.response({'detail': 'Incident not found' if status == 404 else 'Erro'}, status)
            with self.subTest(status=status), patch.object(flow, 'render_candidate_report') as render:
                result, code, out, api, ollama = self.run_flow(investigation=response)
                self.assertEqual((code, result['final_state']), (2, 'INVESTIGATION_FAILED'))
                self.assertEqual(result['investigation_http_status'], status)
                self.assertEqual(result['stage'], 'investigation')
                self.assertIsNone(result['audit_event_id'])
                self.assertEqual((out / 'investigation/response.body').read_bytes(), response.body)
                ollama.assert_not_called()
                render.assert_not_called()

    def test_investigation_transport_error_preserves_partial_raw_response(self):
        result, code, out, api, ollama = self.run_flow(investigation=HTTPResult(None, [], b'partial', 30, 'TimeoutError'))
        self.assertEqual((code, result['final_state'], result['reason_code']), (2, 'INVESTIGATION_FAILED', 'TRANSPORT_ERROR'))
        self.assertEqual((out / 'investigation/response.body').read_bytes(), b'partial')
        ollama.assert_not_called()
        api.assert_called_once()

    def test_exception_connecting_investigation_no_retry(self):
        api, ollama = Mock(side_effect=OSError('connection refused')), Mock()
        result, code = flow.run_flow('INC-001', self.root / 'connection', investigation_transport=api, generation_transport=ollama)
        self.assertEqual(result['final_state'], 'INVESTIGATION_FAILED')
        self.assertEqual(code, 2)
        api.assert_called_once()
        ollama.assert_not_called()

    def test_invalid_ready_evidence_is_context_error_not_normal_inelegibility(self):
        variations = []
        for field in ('logs', 'documentation', 'document_limits'):
            context = deepcopy(self.context)
            if field == 'logs':
                context['logs']['entries'] = []
            else:
                context[field] = []
            variations.append(context)
        context = deepcopy(self.context)
        context['logs']['entries'][0]['message'] = ' '
        context['logs']['entries'][1]['message'] = '\t'
        variations.append(context)
        for context in variations:
            with self.subTest(context=context), patch.object(flow, 'render_candidate_report') as render:
                result, code, out, api, ollama = self.run_flow(investigation=self.response(context))
                self.assertEqual((code, result['final_state']), (2, 'CONTEXT_INVALID'))
                self.assertEqual(result['stage'], 'eligibility')
                ollama.assert_not_called()
                render.assert_not_called()

    def test_malformed_http_200_or_wrong_incident_are_context_errors(self):
        wrong = deepcopy(self.context)
        wrong['incident']['incident_id'] = 'INC-OTHER'
        for body in (b'invalid json', b'[]', self.response(wrong).body):
            result, code, out, api, ollama = self.run_flow(investigation=self.response(body))
            self.assertEqual((code, result['final_state']), (2, 'CONTEXT_INVALID'))
            ollama.assert_not_called()

    def test_structural_rejections_render_rejection_not_error(self):
        for change in ({'cited_chunk_ids': ['outside']}, {'cited_chunk_ids': []}, {'action_type': 'change_environment'}, {'action_type': 'unknown'}):
            with self.subTest(change=change), patch.object(flow, 'render_candidate_report', wraps=flow.render_candidate_report) as render:
                result, code, out, api, ollama = self.run_flow(generated=self.generated_response({**self.candidate, **change}))
                self.assertEqual((code, result['final_state']), (1, 'STRUCTURAL_CHECKS_FAILED'))
                self.assertTrue(result['candidate_produced'])
                self.assertEqual(result['generation_exit_code'], 1)
                render.assert_called_once()
                ollama.assert_called_once()
                text = (out / 'report.md').read_text()
                self.assertIn('Candidata rejeitada', text)
                self.assertIn('Não apresentar esta candidata como orientação a seguir', text)
                self.assertIn('Sustentação semântica não avaliada', text)
                if 'outside' in change.get('cited_chunk_ids', []):
                    self.assertIn('Não encontrada no contexto fornecido', text)
                    self.assertNotIn('Conteúdo integral fornecido:', text)

    def test_generation_errors_are_not_structural_rejections(self):
        responses = [
            HTTPResult(None, [], b'partial', 120, 'TimeoutError'),
            self.response({'error': 'context exceeds available'}, 400),
            self.generated_response(eval_count=256), self.generated_response(done_reason='length'),
            self.generated_response(message={'role': 'assistant', 'content': '```json\n{}\n```'}),
            self.generated_response({**self.candidate, 'text': 123}),
        ]
        for response in responses:
            with self.subTest(response=response), patch.object(flow, 'render_candidate_report') as render:
                result, code, out, api, ollama = self.run_flow(generated=response)
                self.assertEqual((code, result['final_state']), (2, 'GENERATION_FAILED'))
                self.assertFalse(result['candidate_produced'])
                self.assertTrue(result['generation_attempted'])
                self.assertEqual((out / 'generation/response.body').read_bytes(), response.body)
                render.assert_not_called()
                ollama.assert_called_once()
                self.assertIn('Resumo da execução', (out / 'report.md').read_text())
                self.assertNotIn('## Conteúdo fornecido para avaliação', (out / 'report.md').read_text())

    def test_configurable_container_urls_used_exactly(self):
        result, code, out, api, ollama = self.run_flow(api_url='http://ai-app:8000', ollama_url='http://host.docker.internal:11434')
        self.assertEqual(code, 0)
        self.assertEqual(api.call_args.args[0], 'http://ai-app:8000/investigate/INC-001')
        self.assertEqual(ollama.call_args.args[0], 'http://host.docker.internal:11434/api/chat')
        self.assertEqual(json.loads((out / 'parameters.json').read_text())['ollama_url'], 'http://host.docker.internal:11434')

    def test_existing_directory_no_overwrite_and_zero_calls(self):
        out = self.root / 'existing'
        out.mkdir()
        (out / 'sentinel').write_text('original')
        api, ollama = Mock(), Mock()
        result, code = flow.run_flow('INC-001', out, investigation_transport=api, generation_transport=ollama)
        self.assertEqual((code, result['final_state']), (2, 'ARTIFACT_FAILED'))
        self.assertEqual((out / 'sentinel').read_text(), 'original')
        api.assert_not_called()
        ollama.assert_not_called()
        self.assertFalse((out / 'result.json').exists())

    def test_write_failure_before_investigation_zero_calls(self):
        api, ollama = Mock(), Mock()
        with patch.object(flow, 'save_json', side_effect=OSError('disk full')):
            result, code = flow.run_flow('INC-001', self.root / 'disk', investigation_transport=api, generation_transport=ollama)
        self.assertEqual((code, result['final_state']), (2, 'ARTIFACT_FAILED'))
        api.assert_not_called()
        ollama.assert_not_called()

    def test_report_failure_preserves_previous_structural_outcome(self):
        with patch.object(flow, 'render_candidate_report', side_effect=ValueError('render error')):
            result, code, out, api, ollama = self.run_flow()
        self.assertEqual((code, result['final_state']), (2, 'ARTIFACT_FAILED'))
        self.assertEqual(result['previous_outcome']['final_state'], 'STRUCTURAL_CHECKS_PASSED')
        self.assertTrue(result['candidate_produced'])
        self.assertTrue((out / 'generation/response.body').exists())
        self.assertIn('Resumo da execução', (out / 'report.md').read_text())
        ollama.assert_called_once()

    def test_report_write_failure_is_operational_not_success(self):
        real_write = Path.write_text
        attempts = []
        def broken(path, text, *args, **kwargs):
            if path.name == 'report.md':
                attempts.append(str(path))
                raise OSError('read-only report')
            return real_write(path, text, *args, **kwargs)
        with patch.object(Path, 'write_text', new=broken):
            result, code, out, api, ollama = self.run_flow()
        self.assertEqual((code, result['final_state']), (2, 'ARTIFACT_FAILED'))
        self.assertEqual(json.loads((out / 'result.json').read_text())['final_state'], 'ARTIFACT_FAILED')
        self.assertEqual(result['previous_outcome']['final_state'], 'STRUCTURAL_CHECKS_PASSED')
        ollama.assert_called_once()

    def test_error_summary_escapes_untrusted_content(self):
        text = '# title [click](javascript:x) <script>x</script> `code`'
        report = flow.render_summary({'error': text, 'final_state': 'CONTEXT_INVALID'})
        self.assertNotIn('<script>', report)
        self.assertIn('&lt;script&gt;', report)
        self.assertIn('<pre>', report)

    def test_no_duplicate_structural_rule_evaluation(self):
        from recommendation_structure import check_candidate_structure
        with patch.object(flow.generation, 'check_candidate_structure', wraps=check_candidate_structure) as checks:
            result, code, out, api, ollama = self.run_flow()
        checks.assert_called_once()
        self.assertEqual(code, 0)

    def test_incomplete_or_invalid_generator_objects_never_render_candidate(self):
        from recommendation_structure import check_candidate_structure
        structure = check_candidate_structure(
            self.candidate, self.context['documentation'], self.context['document_limits'],
        )
        base = {'status': 'structural_checks_passed', 'candidate': self.candidate, 'structure': structure}
        variations = [
            {**base, 'candidate': {**self.candidate, 'text': 123}},
            {**base, 'structure': {}},
            {k: v for k, v in base.items() if k != 'structure'},
            {**base, 'status': 'structural_checks_failed'},
        ]
        for result in variations:
            with self.subTest(result=result), \
                 patch.object(flow.generation, 'run_experiment', return_value=(result, 0)), \
                 patch.object(flow, 'render_candidate_report') as render:
                outcome, code, out, api, ollama = self.run_flow()
                self.assertEqual((code, outcome['final_state']), (2, 'GENERATION_FAILED'))
                render.assert_not_called()
                self.assertIn('Resumo da execução', (out / 'report.md').read_text())

    def test_cli_prints_state_and_forwards_both_urls(self):
        result = {'final_state': 'NOT_ELIGIBLE', 'candidate_produced': False, 'exit_code': 0}
        with patch.object(flow, 'run_flow', return_value=(result, 0)) as run, redirect_stdout(io.StringIO()) as stdout:
            code = flow.main(['--incident-id', 'INC-002', '--output-dir', '/tmp/new', '--api-url', 'http://ai-app:8000', '--ollama-url', 'http://host.docker.internal:11434'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), result)
        self.assertEqual(run.call_args.args[2:], ('http://ai-app:8000', 'http://host.docker.internal:11434'))

    def test_import_does_not_load_api_embeddings_audit_or_semantic_judge(self):
        import subprocess
        code = "import sys; import investigate_and_report; assert not {'main','search_qdrant','sentence_transformers','audit','judge_claim_examples','claim_judge_models'} & set(sys.modules)"
        result = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
