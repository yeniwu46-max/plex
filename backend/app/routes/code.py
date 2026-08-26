# -*- coding: utf-8 -*-
"""Code execution route - Mock / Judge0 / E2B."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..services.code_execution import CodeExecutionService, LANGUAGE_IDS
from ..utils.response import success_response, error_response
from ..utils.time import utc_now

code_bp = Blueprint('code', __name__, url_prefix='/api/v1')


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
    return success_response(CodeExecutionService.run(language, code, stdin))


@code_bp.post('/code/submit')
@jwt_required()
def submit_code():
    body = request.get_json(silent=True) or {}
    language = body.get('language', 'python')
    code = body.get('code', '')
    test_cases = body.get('test_cases', [])
    run_mode = body.get('run_mode', 'stdout')
    if not code.strip():
        return error_response('code required', code=400)
    if language.lower() not in LANGUAGE_IDS:
        return error_response('unsupported language', code=400)
    if not test_cases:
        run_result = CodeExecutionService.run(language, code)
        return success_response({
            'all_passed': run_result['status']['id'] == 3,
            'passed_count': 1 if run_result['status']['id'] == 3 else 0,
            'total': 1,
            'results': [],
            'submitted_at': utc_now().isoformat(),
            'backend': run_result.get('backend', CodeExecutionService.backend_name()),
        })
    return success_response(CodeExecutionService.submit(language, code, test_cases, run_mode))


@code_bp.get('/code/result/<submission_id>')
@jwt_required()
def get_result(submission_id):
    return success_response({
        'submission_id': submission_id,
        'status': {'id': 3, 'description': 'Accepted'},
        'created_at': utc_now().isoformat(),
        'backend': CodeExecutionService.backend_name(),
    })


@code_bp.post('/code/analyze-file')
@jwt_required()
def analyze_file():
    """返回当前部署的代码文件分析能力状态。"""
    body = request.get_json(silent=True) or {}
    file_id = body.get('fileId', '')
    return error_response('当前部署未启用代码文件分析服务，请联系平台管理员', 50101, {'fileId': file_id}, 501)


@code_bp.get('/code/languages')
def get_languages():
    return success_response({
        'languages': [
            {'id': 71, 'name': 'Python 3', 'key': 'python'},
        ],
        'backend': CodeExecutionService.backend_name(),
    })
