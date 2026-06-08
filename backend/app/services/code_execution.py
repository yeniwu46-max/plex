# -*- coding: utf-8 -*-
"""代码执行：Mock / Judge0 / E2B 可切换。"""
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime

import requests

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


class CodeExecutionService:
    @staticmethod
    def backend_name() -> str:
        if os.getenv('JUDGE0_API_URL', '').strip():
            return 'judge0'
        if os.getenv('E2B_API_KEY', '').strip() and os.getenv('CODE_EXECUTION_BACKEND', '').lower() == 'e2b':
            return 'e2b'
        return 'mock'

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
        return str(value or '').replace('\r\n', '\n').strip()

    @staticmethod
    def _mock_run(language: str, code: str, stdin: str = '') -> dict:
        lang = language.lower()
        token = str(uuid.uuid4())[:8]
        if 'SyntaxError' in code:
            return {
                'token': token,
                'status': {'id': 6, 'description': 'Compilation Error'},
                'stdout': None,
                'stderr': None,
                'compile_output': 'SyntaxError: invalid syntax',
                'time': '0.00',
                'memory': 0,
                'language': lang,
                'backend': 'mock',
            }
        if lang in ('python', 'python3'):
            return CodeExecutionService._mock_run_python(code, stdin, token, lang)
        return {
            'token': token,
            'status': {'id': 6, 'description': 'Unsupported Language'},
            'stdout': None,
            'stderr': 'Only Python is supported',
            'compile_output': None,
            'time': '0.00',
            'memory': 0,
            'language': lang,
            'backend': 'mock',
        }

    @staticmethod
    def _mock_run_python(code: str, stdin: str, token: str, lang: str) -> dict:
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as fh:
            fh.write(code)
            path = fh.name
        try:
            proc = subprocess.run(
                [sys.executable, path],
                input=stdin or '',
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or 'Runtime error').strip()
                return {
                    'token': token,
                    'status': {'id': 11, 'description': 'Runtime Error (NZEC)'},
                    'stdout': proc.stdout or '',
                    'stderr': err,
                    'compile_output': None,
                    'time': '0.010',
                    'memory': 4096,
                    'language': lang,
                    'backend': 'mock',
                }
            return {
                'token': token,
                'status': {'id': 3, 'description': 'Accepted'},
                'stdout': proc.stdout,
                'stderr': proc.stderr or '',
                'compile_output': None,
                'time': '{:.3f}'.format(0.01 + len(code) * 0.00005),
                'memory': 4096 + len(code),
                'language': lang,
                'backend': 'mock',
            }
        except subprocess.TimeoutExpired:
            return {
                'token': token,
                'status': {'id': 5, 'description': 'Time Limit Exceeded'},
                'stdout': '',
                'stderr': 'Execution timed out',
                'compile_output': None,
                'time': '5.000',
                'memory': 4096,
                'language': lang,
                'backend': 'mock',
            }
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    @staticmethod
    def _judge0_run(language: str, code: str, stdin: str = '') -> dict:
        base = os.getenv('JUDGE0_API_URL', '').rstrip('/')
        lang_key = language.lower()
        lang_id = LANGUAGE_IDS.get(lang_key)
        if not lang_id:
            raise ValueError('unsupported language')
        headers = {'Content-Type': 'application/json'}
        auth = os.getenv('JUDGE0_AUTH_TOKEN', '').strip()
        if auth:
            headers['X-Auth-Token'] = auth
        payload = {
            'source_code': code,
            'language_id': lang_id,
            'stdin': stdin or '',
        }
        resp = requests.post(f'{base}/submissions?base64_encoded=false&wait=true', json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status_id = data.get('status', {}).get('id', 13)
        return {
            'token': str(data.get('token', uuid.uuid4())[:8]),
            'status': {
                'id': status_id,
                'description': data.get('status', {}).get('description') or JUDGE0_STATUS.get(status_id, 'Unknown'),
            },
            'stdout': data.get('stdout'),
            'stderr': data.get('stderr'),
            'compile_output': data.get('compile_output'),
            'time': str(data.get('time') or '0.00'),
            'memory': int(data.get('memory') or 0),
            'language': lang_key,
            'backend': 'judge0',
        }

    @staticmethod
    def _e2b_run(code: str, stdin: str = '') -> dict:
        api_key = os.getenv('E2B_API_KEY', '').strip()
        if not api_key:
            raise RuntimeError('E2B_API_KEY not configured')
        from e2b import Sandbox

        token = str(uuid.uuid4())[:8]
        sandbox = Sandbox(api_key=api_key)
        try:
            if stdin.strip():
                wrapped = f"import sys\n_input = '''{stdin}'''\n" + code
            else:
                wrapped = code
            proc = sandbox.process.start_and_wait(wrapped, timeout=10)
            stdout = proc.stdout or ''
            stderr = proc.stderr or ''
            if proc.exit_code != 0:
                return {
                    'token': token,
                    'status': {'id': 11, 'description': 'Runtime Error (NZEC)'},
                    'stdout': stdout,
                    'stderr': stderr or 'Runtime error',
                    'compile_output': None,
                    'time': '0.050',
                    'memory': 8192,
                    'language': 'python',
                    'backend': 'e2b',
                }
            return {
                'token': token,
                'status': {'id': 3, 'description': 'Accepted'},
                'stdout': stdout,
                'stderr': stderr,
                'compile_output': None,
                'time': '0.050',
                'memory': 8192,
                'language': 'python',
                'backend': 'e2b',
            }
        finally:
            sandbox.kill()

    @classmethod
    def run(cls, language: str, code: str, stdin: str = '') -> dict:
        lang = language.lower()
        if lang not in LANGUAGE_IDS:
            raise ValueError('unsupported language')
        backend = cls.backend_name()
        if backend == 'judge0':
            try:
                return cls._judge0_run(language, code, stdin)
            except Exception:
                return cls._mock_run(language, code, stdin)
        if backend == 'e2b' and language.lower() in ('python', 'python3'):
            try:
                return cls._e2b_run(code, stdin)
            except Exception:
                return cls._mock_run(language, code, stdin)
        return cls._mock_run(language, code, stdin)

    @classmethod
    def submit(cls, language: str, code: str, test_cases: list, run_mode: str = 'stdout') -> dict:
        if language.lower() not in LANGUAGE_IDS:
            raise ValueError('unsupported language')
        results = []
        all_passed = True
        for case in test_cases:
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
            passed = run_result['status']['id'] == 3 and (not expected or actual == expected)
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
            'passed_count': sum(1 for x in results if x['passed']),
            'total': len(results),
            'results': results,
            'submitted_at': datetime.utcnow().isoformat(),
            'backend': cls.backend_name(),
        }
