# -*- coding: utf-8 -*-
"""Isolated execution only. Infrastructure errors never become grades."""
import os
import time
import json
import uuid
import requests
from flask import current_app, has_app_context

from .execution_errors import ExecutionInputError, ExecutionUnavailable

from app.utils.time import utc_now

LANGUAGE_IDS = {
    'python': 71,
    'python3': 71,
}

JUDGE0_STATUS = {
    1: 'In Queue',
    2: 'Processing',
    3: 'Accepted',
    4: 'Wrong Answer',
    5: 'Time Limit Exceeded',
    6: 'Compilation Error',
    7: 'Memory Limit Exceeded',
    9: 'Runtime Error (SIGSEGV)',
    11: 'Runtime Error (NZEC)',
}

FULLWIDTH_PYTHON_SYMBOLS = {
    '\u3000': ' ',
    '（': '(', '）': ')',
    '［': '[', '］': ']',
    '｛': '{', '｝': '}',
    '，': ',', '：': ':', '；': ';',
    '＝': '=', '＋': '+', '－': '-', '＊': '*', '／': '/', '％': '%',
    '＜': '<', '＞': '>', '！': '!',
    '＂': '"', '＇': "'",
}


class CodeExecutionService:
    @staticmethod
    def normalize_python_source(source: str) -> str:
        """Normalize IME full-width syntax while preserving strings/comments."""
        result = []
        quote = None
        triple_quoted = False
        escaped = False
        in_comment = False
        index = 0

        def normalized_at(position: int) -> str:
            if position >= len(source):
                return ''
            char = source[position]
            return FULLWIDTH_PYTHON_SYMBOLS.get(char, char)

        while index < len(source):
            char = source[index]
            normalized = FULLWIDTH_PYTHON_SYMBOLS.get(char, char)

            if in_comment:
                result.append(char)
                if char == '\n':
                    in_comment = False
                index += 1
                continue

            if quote:
                if triple_quoted:
                    if (
                        normalized == quote
                        and normalized_at(index + 1) == quote
                        and normalized_at(index + 2) == quote
                    ):
                        result.append(quote * 3)
                        index += 3
                        quote = None
                        triple_quoted = False
                    else:
                        result.append(char)
                        index += 1
                    continue

                if escaped:
                    result.append(char)
                    escaped = False
                elif char == '\\':
                    result.append(char)
                    escaped = True
                elif normalized == quote:
                    result.append(quote)
                    quote = None
                else:
                    result.append(char)
                index += 1
                continue

            if char == '#':
                in_comment = True
                result.append(char)
                index += 1
                continue

            if normalized in {"'", '"'}:
                quote = normalized
                triple_quoted = (
                    normalized_at(index + 1) == quote
                    and normalized_at(index + 2) == quote
                )
                count = 3 if triple_quoted else 1
                result.append(quote * count)
                index += count
                continue

            result.append(normalized)
            index += 1

        return ''.join(result)

    @staticmethod
    def _setting(name: str, default: str = '') -> str:
        if has_app_context() and name in current_app.config:
            return str(current_app.config[name])
        return os.getenv(name, default)

    @classmethod
    def backend_name(cls) -> str:
        selected = cls._setting('CODE_EXECUTION_BACKEND', 'auto').strip().lower()
        if selected == 'auto':
            return 'judge0' if cls._setting('JUDGE0_API_URL').strip() else 'disabled'
        # The legacy "mock" and E2B process adapter do not meet the execution
        # contract. They are deliberately disabled, never a host fallback.
        return selected if selected in {'judge0', 'docker'} else 'disabled'

    @classmethod
    def capabilities(cls) -> dict:
        backend = cls.backend_name()
        from .python_trace import PythonTraceService
        return {'trace': PythonTraceService.capabilities(), 'backend': backend, 'configured': backend != 'disabled',
                'isolation_required': True, 'host_fallback': False,
                'max_code_bytes': 65536, 'max_stdin_bytes': 65536,
                'max_test_cases': 30}

    @staticmethod
    def wrap_python_case(code: str, setup: str = '', invoke: str = '', run_mode: str = 'stdout') -> str:
        parts = []
        if setup.strip():
            parts.append(setup.strip())
        parts.append(code.strip())
        if run_mode == 'expression' and invoke:
            parts.append(f'_plex_result = {invoke}')
            parts.append('print(_plex_result)')
        return '\n'.join(parts) + '\n'

    @staticmethod
    def _normalize_output(value) -> str:
        return str(value if value is not None else '').replace('\r\n', '\n').strip()

    @staticmethod
    def _judge0_run(language: str, code: str, stdin: str = '') -> dict:
        base = CodeExecutionService._setting('JUDGE0_API_URL').rstrip('/')
        lang_key = language.lower()
        lang_id = LANGUAGE_IDS.get(lang_key)
        if not lang_id:
            raise ValueError('unsupported language')
        headers = {'Content-Type': 'application/json'}
        auth = CodeExecutionService._setting('JUDGE0_AUTH_TOKEN').strip()
        if auth:
            headers['X-Auth-Token'] = auth
        payload = {
            'source_code': code,
            'language_id': lang_id,
            'stdin': stdin or '',
            'cpu_time_limit': 3, 'wall_time_limit': 8,
            'memory_limit': 131072, 'max_processes_and_or_threads': 32,
            'max_file_size': 64, 'enable_network': False,
        }
        with requests.post(f'{base}/submissions?base64_encoded=false&wait=true',
                           json=payload, headers=headers, timeout=(3, 12), stream=True) as resp:
            resp.raise_for_status()
            body = bytearray()
            started = time.monotonic()
            for chunk in resp.iter_content(4096):
                body.extend(chunk)
                if len(body) > 262144 or time.monotonic() - started > 15:
                    raise ExecutionUnavailable('judge_response_limit')
            data = json.loads(body)
        status_id = data.get('status', {}).get('id', 13)
        if status_id not in {3, 4, 5, 6, 7, 8, 9, 10, 11, 12} or data.get('message'):
            raise ExecutionUnavailable('judge_unfinished_or_failed')
        if any(len(str(data.get(key) or '').encode('utf-8')) > 65536 for key in ('stdout', 'stderr', 'compile_output')):
            raise ExecutionUnavailable('judge_output_limit')
        return {
            'token': str(data.get('token') or uuid.uuid4()),
            'status': {
                'id': status_id,
                'description': data.get('status', {}).get('description') or JUDGE0_STATUS.get(status_id, 'Unknown'),
            },
            'stdout': data.get('stdout'),
            'stderr': data.get('stderr'),
            'compile_output': data.get('compile_output'),
            'time': data.get('time'),
            'memory': data.get('memory'),
            'language': lang_key,
            'backend': 'judge0',
        }

    @classmethod
    def run(cls, language: str, code: str, stdin: str = '') -> dict:
        if not isinstance(language, str) or language.lower() not in LANGUAGE_IDS:
            raise ExecutionInputError('仅支持 Python')
        for label, value in (('code', code), ('stdin', stdin)):
            if not isinstance(value, str) or len(value.encode('utf-8')) > 65536:
                raise ExecutionInputError(f'{label} 必须是最多 64 KiB 的文本')
        if not code.strip():
            raise ExecutionInputError('code 不能为空')
        code = cls.normalize_python_source(code)
        backend = cls.backend_name()
        try:
            if backend == 'judge0':
                return cls._judge0_run(language, code, stdin)
            if backend == 'docker':
                from .docker_execution import run_container
                return run_container(code, stdin, image=cls._setting(
                    'CODE_EXECUTION_DOCKER_IMAGE', 'plex-python-sandbox:1'))
        except ExecutionUnavailable:
            raise
        except Exception as exc:
            # Do not expose provider URLs, credentials or host error details.
            raise ExecutionUnavailable('provider_failed') from exc
        raise ExecutionUnavailable('not_configured')

    @classmethod
    def validate_submission(cls, language: str, code: str, test_cases: list, run_mode: str = 'stdout') -> None:
        if not isinstance(language, str) or language.lower() not in LANGUAGE_IDS:
            raise ExecutionInputError('仅支持 Python')
        if not isinstance(test_cases, list) or not 1 <= len(test_cases) <= 30:
            raise ExecutionInputError('需要 1–30 个测试用例')
        if not isinstance(run_mode, str) or run_mode not in {'stdout', 'expression'}:
            raise ExecutionInputError('无效的 run_mode')
        for case in test_cases:
            if not isinstance(case, dict) or 'expected' not in case:
                raise ExecutionInputError('每个测试用例必须有 expected（可以为空字符串）')
            if any(not isinstance(case.get(key, ''), str) for key in ('setup', 'invoke', 'input')):
                raise ExecutionInputError('用例 setup、invoke、input 必须是文本')
        if not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 65536:
            raise ExecutionInputError('code 必须是非空且最多 64 KiB 的文本')

    @classmethod
    def submit(cls, language: str, code: str, test_cases: list, run_mode: str = 'stdout') -> dict:
        cls.validate_submission(language, code, test_cases, run_mode)
        started = time.monotonic()
        results = []
        all_passed = True
        for case in test_cases:
            if time.monotonic() - started > 60:
                raise ExecutionUnavailable('submission_budget_exceeded')
            setup = case.get('setup') or ''
            invoke = case.get('invoke') or ''
            stdin = case.get('input') or ''
            if language.lower() in ('python', 'python3'):
                case_code = cls.wrap_python_case(code, setup, invoke, run_mode)
            else:
                raise ValueError('unsupported language')
            run_result = cls.run(language, case_code, stdin)
            expected = cls._normalize_output(case.get('expected', ''))
            actual = cls._normalize_output(run_result.get('stdout'))
            passed = run_result['status']['id'] == 3 and actual == expected
            if not passed:
                all_passed = False
            error_msg = None
            if run_result['status']['id'] != 3:
                error_msg = run_result.get('stderr') or run_result.get('compile_output') or run_result['status']['description']
            results.append({
                'case_id': case.get('id', ''),
                'label': case.get('label', ''),
                'passed': passed,
                'expected': expected,
                'actual': actual,
                'status': run_result['status'],
                'time': run_result['time'],
                'memory': run_result['memory'],
                'error': error_msg,
            })
        return {
            'all_passed': all_passed,
            'evidence_scope': 'self_test',
            'passed_count': sum(1 for x in results if x['passed']),
            'total': len(results),
            'results': results,
            'submitted_at': utc_now().isoformat(),
            'backend': cls.backend_name(),
        }
