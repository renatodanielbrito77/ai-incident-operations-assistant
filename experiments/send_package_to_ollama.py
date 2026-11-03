"""Experimento manual: uma chamada ao Ollama, sem API, audit ou execução de ações."""

import argparse
from dataclasses import dataclass
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ai-app'))
from llm_input_models import LLMInputPackage
from recommendation_models import CandidateStructureReport, RecommendationCandidate
from recommendation_structure import check_candidate_structure

MODEL = 'qwen3:1.7b'
NUM_CTX = 4096
NUM_PREDICT = 256
TIMEOUT_SECONDS = 120


def read_json(text):
    """Não aceita constantes não JSON nem chaves duplicadas; não repara a saída."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Chave JSON duplicada: {key}')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f'Constante não JSON: {value}')

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


def make_request(package):
    # Todos os campos do pacote permanecem nas mensagens; somente instructions
    # ocupa system. Nenhuma evidência é promovida a instrução da aplicação.
    data = package.model_dump(mode='json')
    instructions = data.pop('instructions')
    return {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': json.dumps(instructions, ensure_ascii=False)},
            {'role': 'user', 'content': json.dumps(data, ensure_ascii=False)},
        ],
        'format': RecommendationCandidate.model_json_schema(),
        'stream': False, 'think': False, 'truncate': False, 'shift': False,
        'keep_alive': 0,
        'options': {'num_ctx': NUM_CTX, 'num_predict': NUM_PREDICT, 'temperature': 0},
    }


@dataclass
class HTTPResult:
    status: int | None
    headers: list
    body: bytes
    elapsed_seconds: float
    error: str | None = None


def post_once(url, payload, timeout):
    """HTTP sem redirect/retry; deadline total e preservação do corpo recebido."""
    address = urlsplit(url)
    if address.scheme != 'http' or not address.hostname or address.username or address.password:
        raise ValueError('Use uma URL HTTP explícita para o Ollama local, sem credenciais')
    if address.query or address.fragment:
        raise ValueError('A URL não deve conter query ou fragmento')
    connection = http.client.HTTPConnection(address.hostname, address.port or 80, timeout=timeout)
    started = time.monotonic()
    deadline = started + timeout
    status, headers, chunks, error = None, [], [], None
    try:
        connection.request('POST', address.path or '/', body=payload,
                           headers={'Content-Type': 'application/json'})
        sock = connection.sock
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Deadline total excedido')
        sock.settimeout(remaining)
        response = connection.getresponse()
        status, headers = response.status, response.getheaders()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Deadline total excedido')
            sock.settimeout(remaining)
            chunk = response.read1(65536)
            if not chunk:
                break
            chunks.append(chunk)
        lengths = [value for key, value in headers if key.lower() == 'content-length']
        if lengths and (not lengths[0].isdigit() or sum(map(len, chunks)) != int(lengths[0])):
            error = 'IncompleteHTTPBody: corpo recebido difere de Content-Length'
    except http.client.IncompleteRead as exc:
        chunks.append(exc.partial)
        error = f'IncompleteRead: {exc}'
    except (OSError, http.client.HTTPException) as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        connection.close()
    return HTTPResult(status, headers, b''.join(chunks), time.monotonic() - started, error)


def evaluate_response(response, package):
    """Só interpreta a candidata depois de verificar a conclusão e os limites."""
    result = {
        'status': 'operational_error', 'code': 'TRANSPORT_ERROR',
        'elapsed_seconds': response.elapsed_seconds, 'http_status': response.status,
        'semantic_support_status': 'not_evaluated',
    }
    if response.error:
        return {**result, 'error': response.error}, 2
    try:
        body = read_json(response.body.decode('utf-8'))
    except (UnicodeError, ValueError) as exc:
        return {**result, 'code': 'INVALID_HTTP_JSON', 'error': str(exc)}, 2
    if not isinstance(body, dict):
        return {**result, 'code': 'INVALID_HTTP_ENVELOPE'}, 2
    result['indicators'] = {k: v for k, v in body.items() if k != 'message'}
    if response.status != 200 or 'error' in body:
        return {**result, 'code': 'OLLAMA_ERROR', 'error': body.get('error', 'HTTP inesperado')}, 2
    result.update(status='output_rejected', code='INCOMPLETE_GENERATION')
    if body.get('done') is not True or body.get('done_reason') != 'stop':
        return result, 1
    count, prompt = body.get('eval_count'), body.get('prompt_eval_count')
    if type(count) is not int or type(prompt) is not int or count < 1 or prompt < 1:
        return {**result, 'code': 'INVALID_TOKEN_INDICATORS'}, 2
    if count >= NUM_PREDICT:
        return {**result, 'code': 'GENERATION_LIMIT'}, 1
    # Além da proteção truncate:false, exige reserva inteira para a saída.
    # A contagem informada não é, isoladamente, prova contra truncamento.
    if prompt + NUM_PREDICT > NUM_CTX:
        return {**result, 'code': 'CONTEXT_NOT_VERIFIED'}, 2
    message = body.get('message')
    if not isinstance(message, dict) or message.get('role') != 'assistant':
        return {**result, 'code': 'INVALID_MESSAGE'}, 2
    if message.get('thinking') or message.get('tool_calls'):
        return {**result, 'code': 'UNEXPECTED_THINKING_OR_TOOL_CALL'}, 1
    content = message.get('content')
    if not isinstance(content, str):
        return {**result, 'code': 'INVALID_CANDIDATE_JSON'}, 1
    try:
        data = read_json(content)
    except ValueError as exc:
        return {**result, 'code': 'INVALID_CANDIDATE_JSON', 'error': str(exc)}, 1
    try:
        candidate = RecommendationCandidate.model_validate(data, strict=True)
    except ValueError as exc:
        return {**result, 'code': 'INVALID_CANDIDATE_CONTRACT', 'error': str(exc)}, 1
    report = CandidateStructureReport.model_validate(check_candidate_structure(
        candidate.model_dump(),
        [item.model_dump() for item in package.evidence.documentation],
        [item.model_dump() for item in package.evidence.document_limits],
    ), strict=True)
    result.update(
        status='structural_checks_passed' if report.structural_checks_passed else 'structural_checks_failed',
        code='STRUCTURE_EVALUATED', candidate=candidate.model_dump(), structure=report.model_dump(),
    )
    return result, 0 if report.structural_checks_passed else 1


def run_experiment(package_path, output_dir, base_url='http://127.0.0.1:11434', transport=None):
    """Diretório novo obrigatório. Nunca consulta incidentes nem grava no audit."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    parameters = {
        'model': MODEL, 'num_ctx': NUM_CTX, 'num_predict': NUM_PREDICT,
        'timeout_seconds': TIMEOUT_SECONDS, 'base_url': base_url,
        'truncate': False, 'shift': False, 'think': False, 'stream': False,
        'context_compatibility': 'Entrada excedente rejeitada em teste separado no Ollama 0.40.14; não é uma consulta de versão nesta execução.',
    }

    def save(name, value):
        (output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

    def finish(result, code):
        result['exit_code'] = code
        save('result.json', result)
        if 'candidate' in result:
            save('candidate.json', result['candidate'])
        return result, code

    save('parameters.json', parameters)
    try:
        raw_package = Path(package_path).read_bytes()
        (output_dir / 'package.json').write_bytes(raw_package)
        package = LLMInputPackage.model_validate(read_json(raw_package.decode('utf-8')), strict=True)
    except (OSError, UnicodeError, ValueError) as exc:
        return finish({'status': 'input_error', 'code': 'INVALID_READY_PACKAGE', 'error': str(exc)}, 2)
    request = make_request(package)
    payload = json.dumps(request, ensure_ascii=False, allow_nan=False).encode('utf-8')
    (output_dir / 'request.json').write_bytes(payload)
    save('input_metadata.json', {
        'incident_id': package.incident_id, 'audit_event_id': package.audit_event_id,
        'package_characters': len(raw_package.decode('utf-8')), 'package_bytes': len(raw_package),
        'package_sha256': hashlib.sha256(raw_package).hexdigest(),
        'request_bytes': len(payload), 'request_sha256': hashlib.sha256(payload).hexdigest(),
    })
    try:
        response = (transport or post_once)(base_url.rstrip('/') + '/api/chat', payload, TIMEOUT_SECONDS)
    except (OSError, ValueError) as exc:
        return finish({'status': 'operational_error', 'code': 'TRANSPORT_ERROR', 'error': str(exc)}, 2)
    (output_dir / 'response.body').write_bytes(response.body)
    save('response_http.json', {
        'status': response.status, 'headers': response.headers,
        'elapsed_seconds': response.elapsed_seconds, 'transport_error': response.error,
    })
    result, code = evaluate_response(response, package)
    return finish(result, code)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True, help='Diretório novo, ainda inexistente')
    parser.add_argument('--base-url', default='http://127.0.0.1:11434')
    args = parser.parse_args(argv)
    try:
        result, code = run_experiment(args.package, args.output_dir, args.base_url)
    except (OSError, ValueError) as exc:
        print(f'Erro operacional: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
