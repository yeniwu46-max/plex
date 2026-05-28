# -*- coding: utf-8 -*-
"""Code execution route - Mock Judge0 first phase."""
import uuid
from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..utils.response import success_response, error_response

code_bp = Blueprint('code', __name__, url_prefix='/api/v1')

LANGUAGE_IDS = {
    'python': 71, 'python3': 71,
    'javascript': 63, 'js': 63,
    'c': 49, 'cpp': 54, 'java': 62,
}


def _mock_run(language, code, stdin=''):
    lang = language.lower()
    token = str(uuid.uuid4())[:8]
    has_output = any(kw in code for kw in ['print(', 'console.log('])
    if 'SyntaxError' in code:
        return {
            'token': token,
            'status': {'id': 6, 'description': 'Compilation Error'},
            'stdout': None, 'stderr': None,
            'compile_output': 'SyntaxError: invalid syntax',
            'time': '0.00', 'memory': 0, 'language': lang,
        }
    return {
        'token': token,
        'status': {'id': 3, 'description': 'Accepted'},
        'stdout': 'Hello, PLEX!\n' if has_output else '',
        'stderr': '', 'compile_output': None,
        'time': '{:.3f}'.format(0.05 + len(code) * 0.0001),
        'memory': 3200 + len(code) * 2, 'language': lang,
    }


def _mock_submit(language, code, test_cases):
    results = []
    all_passed = True
    for case in test_cases:
        r = _mock_run(language, code, case.get('input', ''))
        expected = str(case.get('expected', '')).strip()
        actual = str(r.get('stdout', '') or '').strip()
        passed = r['status']['id'] == 3 and (not expected or actual == expected)
        if not passed:
            all_passed = False
        results.append({
            'case_id': case.get('id', ''), 'label': case.get('label', ''),
            'passed': passed, 'expected': expected, 'actual': actual,
            'status': r['status'], 'time': r['time'], 'memory': r['memory'],
        })
    return {
        'all_passed': all_passed,
        'passed_count': sum(1 for x in results if x['passed']),
        'total': len(results), 'results': results,
        'submitted_at': datetime.utcnow().isoformat(),
    }


@code_bp.post('/code/run')
@jwt_required()
def run_code():
    body = request.get_json(silent=True) or {}
    language = body.get('language', 'python')
    code = body.get('code', '')
    stdin = body.get('stdin', '')
    if not code.strip():
        return error_response('code required', code=400)
    if language.lower() not in LANGUAGE_IDS:
        return error_response('unsupported language', code=400)
    return success_response(_mock_run(language, code, stdin))


@code_bp.post('/code/submit')
@jwt_required()
def submit_code():
    body = request.get_json(silent=True) or {}
    language = body.get('language', 'python')
    code = body.get('code', '')
    test_cases = body.get('test_cases', [])
    if not code.strip():
        return error_response('code required', code=400)
    if not test_cases:
        r = _mock_run(language, code)
        return success_response({
            'all_passed': r['status']['id'] == 3,
            'passed_count': 1 if r['status']['id'] == 3 else 0,
            'total': 1, 'results': [],
        })
    return success_response(_mock_submit(language, code, test_cases))


@code_bp.get('/code/result/<submission_id>')
@jwt_required()
def get_result(submission_id):
    return success_response({
        'submission_id': submission_id,
        'status': {'id': 3, 'description': 'Accepted'},
        'created_at': datetime.utcnow().isoformat(),
    })


@code_bp.get('/code/languages')
def get_languages():
    return success_response({'languages': [
        {'id': 71, 'name': 'Python 3', 'key': 'python'},
        {'id': 63, 'name': 'JavaScript', 'key': 'javascript'},
        {'id': 54, 'name': 'C++', 'key': 'cpp'},
        {'id': 49, 'name': 'C', 'key': 'c'},
        {'id': 62, 'name': 'Java', 'key': 'java'},
    ]})
