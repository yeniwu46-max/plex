# -*- coding: utf-8 -*-
"""Self-test execution; official assessment uses server-owned questions."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services.code_execution import CodeExecutionService, LANGUAGE_IDS
from ..utils.response import success_response, error_response
from ..services.execution_errors import ExecutionInputError
from ..services.tutor_context import TutorContextService
from ..models import db, User
from ..utils.decorators import role_required


def _context(body):
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if user and user.role and user.role.name == 'student':
        return TutorContextService.resolve(uid, body)
    return None

code_bp = Blueprint('code', __name__, url_prefix='/api/v1')


def _body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ExecutionInputError('请求体必须是 JSON 对象')
    if not isinstance(body.get('code'), str) or not body['code'].strip():
        raise ExecutionInputError('code 不能为空')
    if not isinstance(body.get('language', 'python'), str):
        raise ExecutionInputError('language 必须是文本')
    return body


@code_bp.post('/code/run')
@jwt_required()
def run_code():
    body = _body()
    language = body.get('language', 'python')
    code = body.get('code', '')
    stdin = body.get('stdin', '')
    context = _context(body)
    result = CodeExecutionService.run(language, code, stdin)
    if context:
        result.update(TutorContextService.record_run(int(get_jwt_identity()), context, result, kind='run'))
    return success_response(result)


@code_bp.post('/code/trace')
@jwt_required()
@role_required('student')
def trace_code():
    from ..services.python_trace import PythonTraceService
    from ..services.tutor_context import TutorContextError
    body = _body()
    if set(body) - {'code','stdin','language','formal_question_id','question_ref','question_version'}:
        raise ExecutionInputError('轨迹请求包含不支持的字段')
    if body.get('language', 'python').lower() not in LANGUAGE_IDS:
        raise ExecutionInputError('执行轨迹仅支持 Python')
    context = _context(body)
    db.session.rollback()
    result = PythonTraceService.run(body['code'], body.get('stdin', ''))
    if not TutorContextService.current(int(get_jwt_identity()), context):
        raise TutorContextError('题目或权限已变化，请重新加载后查看轨迹', 409)
    result.update(TutorContextService.record_run(int(get_jwt_identity()), context, result, kind='trace'))
    return success_response(result)


@code_bp.post('/code/submit')
@jwt_required()
def submit_code():
    body = _body()
    language = body.get('language', 'python')
    code = body.get('code', '')
    test_cases = body.get('test_cases', [])
    run_mode = body.get('run_mode', 'stdout')
    context = _context(body)
    result = CodeExecutionService.submit(language, code, test_cases, run_mode)
    if context:
        result.update(TutorContextService.record_run(int(get_jwt_identity()), context, result, kind='test_cases'))
    return success_response(result)


@code_bp.get('/code/result/<submission_id>')
@jwt_required()
def get_result(submission_id):
    # Synchronous self-tests have no persistent submission token. Never invent
    # an Accepted verdict for an arbitrary identifier.
    return error_response('该执行记录不存在，请查看运行请求返回的结果', 40401, None, 404)


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
        'execution': CodeExecutionService.capabilities(),
    })
