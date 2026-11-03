"""Compõe investigação, elegibilidade, geração e relatório, sem executar ações.

Código 0 também inclui NOT_ELIGIBLE: consulte final_state e candidate_produced.
No container, 127.0.0.1 é o próprio container; configure --api-url e --ollama-url.
O Ollama no Mac pode ser acessado por http://host.docker.internal:11434.
"""

import argparse
from html import escape
import json
from pathlib import Path
import sys
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ai-app'))
from llm_input_package import build_llm_input_package, serialize_llm_input_package
from recommendation_models import RecommendationCandidate, CandidateStructureReport
from recommendation_report import render_candidate_report
import send_package_to_ollama as generation

INVESTIGATION_TIMEOUT_SECONDS = 30


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def render_summary(result):
    """Resumo de encerramento/erro: não fabrica candidata ou relatório estrutural."""
    return '\n'.join([
        '# Resumo da execução', '',
        '> Código 0 não significa candidata produzida; consulte final_state.',
        '> Sustentação semântica não avaliada. Este resumo não autoriza ações.', '',
        '<pre>' + escape(json.dumps(result, ensure_ascii=False, indent=2), quote=True) + '</pre>', '',
    ])


def run_flow(incident_id, output_dir, api_url='http://127.0.0.1:8000',
             ollama_url='http://127.0.0.1:11434',
             investigation_transport=None, generation_transport=None):
    output_dir = Path(output_dir)
    result = {
        'final_state': None, 'stage': 'artifact_creation', 'reason_code': None,
        'incident_id': incident_id, 'audit_event_id': None,
        'candidate_produced': False, 'generation_attempted': False,
        'semantic_support_status': 'not_evaluated', 'requested_model': generation.MODEL,
    }
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        return {**result, 'final_state': 'ARTIFACT_FAILED', 'reason_code': 'OUTPUT_DIRECTORY',
                'error': str(exc), 'exit_code': 2}, 2

    def finish(state, reason, code, report=None):
        result.update(final_state=state, reason_code=reason, exit_code=code)
        save_json(output_dir / 'result.json', result)
        text = render_summary(result) if report is None else report
        (output_dir / 'report.md').write_text(text, encoding='utf-8')
        return result, code

    try:
        parameters = {
            'api_url': api_url, 'ollama_url': ollama_url,
            'investigation_timeout_seconds': INVESTIGATION_TIMEOUT_SECONDS,
            'generation': {
                'model': generation.MODEL, 'num_ctx': generation.NUM_CTX,
                'num_predict': generation.NUM_PREDICT, 'timeout_seconds': generation.TIMEOUT_SECONDS,
                'temperature': 0, 'truncate': False, 'shift': False, 'think': False,
                'stream': False, 'keep_alive': 0,
            },
            'instructions_source': 'official build_llm_input_package', 'policy_version': None,
        }
        save_json(output_dir / 'parameters.json', parameters)
        result['stage'] = 'investigation'
        if not isinstance(incident_id, str) or not incident_id.strip():
            return finish('INVESTIGATION_FAILED', 'INVALID_INCIDENT_ID', 2)
        investigation_dir = output_dir / 'investigation'
        investigation_dir.mkdir()
        url = api_url.rstrip('/') + '/investigate/' + quote(incident_id, safe='')
        save_json(investigation_dir / 'request.json', {
            'method': 'POST', 'url': url, 'body': '',
            'timeout_seconds': INVESTIGATION_TIMEOUT_SECONDS,
        })
        try:
            response = (investigation_transport or generation.post_once)(url, b'', INVESTIGATION_TIMEOUT_SECONDS)
        except (OSError, ValueError) as exc:
            result['error'] = str(exc)
            return finish('INVESTIGATION_FAILED', 'TRANSPORT_ERROR', 2)
        (investigation_dir / 'response.body').write_bytes(response.body)
        save_json(investigation_dir / 'response_http.json', {
            'status': response.status, 'headers': response.headers,
            'elapsed_seconds': response.elapsed_seconds, 'transport_error': response.error,
        })
        result['investigation_http_status'] = response.status
        if response.error:
            result['error'] = response.error
            return finish('INVESTIGATION_FAILED', 'TRANSPORT_ERROR', 2)
        if response.status != 200:
            return finish('INVESTIGATION_FAILED', 'HTTP_ERROR', 2)
        result['stage'] = 'eligibility'
        try:
            body = generation.read_json(response.body.decode('utf-8'))
            if not isinstance(body, dict):
                raise ValueError('Resposta de investigação deve ser um objeto JSON')
            supplied_id = body.get('audit_event_id')
            if isinstance(supplied_id, str) and supplied_id.strip():
                result['audit_event_id'] = supplied_id
            eligibility = build_llm_input_package(body)
            source_incident_id = eligibility.package.incident_id if eligibility.status == 'ready' else eligibility.incident_id
            if source_incident_id != incident_id:
                raise ValueError('Incidente da resposta não corresponde ao incidente solicitado')
        except (UnicodeError, ValueError) as exc:
            result['error'] = str(exc)
            return finish('CONTEXT_INVALID', 'INVALID_INVESTIGATION_CONTEXT', 2)
        if eligibility.status == 'not_eligible':
            result['audit_event_id'] = eligibility.audit_event_id
            return finish('NOT_ELIGIBLE', eligibility.reason_code, 0)
        package = eligibility.package
        result['audit_event_id'] = package.audit_event_id
        parameters['policy_version'] = package.instructions.policy_version
        save_json(output_dir / 'parameters.json', parameters)
        package_path = output_dir / 'package.json'
        package_path.write_text(serialize_llm_input_package(package), encoding='utf-8')
        result.update(stage='generation', generation_attempted=True)
        generated, original_code = generation.run_experiment(
            package_path, output_dir / 'generation', base_url=ollama_url,
            transport=generation_transport,
        )
        result['generation_result'] = generated
        result['generation_exit_code'] = original_code
        if generated.get('status') not in {'structural_checks_passed', 'structural_checks_failed'}:
            return finish('GENERATION_FAILED', generated.get('code', 'INVALID_GENERATION_RESULT'), 2)
        # Reconstrói os objetos já validados pelo executor. Não recalcula as
        # regras de referências/ação nem a decisão estrutural.
        try:
            candidate = RecommendationCandidate.model_validate(generated['candidate'], strict=True)
            structure = CandidateStructureReport.model_validate(generated['structure'], strict=True)
            if (generated['status'] == 'structural_checks_passed') != structure.structural_checks_passed:
                raise ValueError('Estado do executor difere do relatório estrutural')
        except (ValueError, KeyError) as exc:
            result['error'] = str(exc)
            return finish('GENERATION_FAILED', 'INVALID_GENERATION_RESULT', 2)
        result.update(candidate_produced=True, stage='report')
        state = 'STRUCTURAL_CHECKS_PASSED' if structure.structural_checks_passed else 'STRUCTURAL_CHECKS_FAILED'
        code = 0 if structure.structural_checks_passed else 1
        # Registra o resultado anterior para preservá-lo se a apresentação falhar.
        result.update(final_state=state, reason_code='STRUCTURE_EVALUATED', exit_code=code)
        try:
            text = render_candidate_report(
                candidate, structure,
                [item.model_dump() for item in package.evidence.documentation],
                [item.model_dump() for item in package.evidence.document_limits],
            )
        except ValueError as exc:
            raise OSError(f'Falha ao gerar relatório: {exc}') from exc
        metadata = {
            'final_state': state, 'audit_event_id': package.audit_event_id,
            'model_requested': generation.MODEL,
            'model_returned': generated.get('indicators', {}).get('model'),
            'parameters': parameters['generation'], 'policy_version': parameters['policy_version'],
            'semantic_support_status': 'not_evaluated',
        }
        text += '\n## Metadados da execução\n\n<pre>' + escape(json.dumps(metadata, ensure_ascii=False, indent=2), quote=True) + '</pre>\n'
        return finish(state, 'STRUCTURE_EVALUATED', code, report=text)
    except OSError as exc:
        failure = {
            **result, 'final_state': 'ARTIFACT_FAILED', 'reason_code': 'ARTIFACT_WRITE_OR_RENDER',
            'error': str(exc), 'exit_code': 2, 'previous_outcome': dict(result),
        }
        # Se o destino estiver indisponível, o resultado ainda é devolvido à CLI.
        try:
            save_json(output_dir / 'result.json', failure)
            (output_dir / 'report.md').write_text(render_summary(failure), encoding='utf-8')
        except OSError:
            pass
        return failure, 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--incident-id', required=True)
    parser.add_argument('--output-dir', required=True, type=Path, help='Diretório novo; nunca sobrescrito')
    parser.add_argument('--api-url', default='http://127.0.0.1:8000',
                        help='No Compose, por exemplo http://ai-app:8000; localhost é o próprio container')
    parser.add_argument('--ollama-url', default='http://127.0.0.1:11434',
                        help='Para Ollama no Mac a partir do container: http://host.docker.internal:11434')
    args = parser.parse_args(argv)
    result, code = run_flow(args.incident_id, args.output_dir, args.api_url, args.ollama_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
