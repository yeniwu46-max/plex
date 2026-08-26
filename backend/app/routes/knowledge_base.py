# -*- coding: utf-8 -*-
"""Knowledge base route - RAG service."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..services.course_safety import SafetyViolation
from ..services.rag_service import RagService
from ..utils.decorators import role_required
from ..utils.response import error_response, success_response

kb_bp = Blueprint('knowledge_base', __name__, url_prefix='/api/v1')


@kb_bp.post('/kb/upload')
@jwt_required()
@role_required('teacher', 'admin')
def upload_document():
    file = request.files.get('file')
    if not file or not file.filename:
        return error_response('file required', code=400)
    return success_response(RagService.upload(file.filename))


@kb_bp.post('/kb/query')
@jwt_required()
def query_knowledge():
    body = request.get_json(silent=True) or {}
    question = body.get('question', '').strip()
    if not question:
        return error_response('question required', code=400)
    try:
        result = RagService.query(question)
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)
    return success_response({
        'question': question,
        **result,
        'queried_at': RagService.status()['last_sync'],
    })


@kb_bp.get('/kb/documents')
@jwt_required()
@role_required('teacher', 'admin')
def list_documents():
    return success_response(RagService.list_documents())


@kb_bp.get('/kb/status')
@jwt_required()
@role_required('teacher', 'admin')
def kb_status():
    return success_response(RagService.status())


@kb_bp.post('/kb/parse-document')
@jwt_required()
@role_required('teacher', 'admin')
def parse_document():
    """返回当前部署的知识库文档解析能力状态。"""
    body = request.get_json(silent=True) or {}
    file_id = body.get('fileId', '')
    return error_response('当前部署未启用知识库文档解析服务，请联系平台管理员', 50101, {'fileId': file_id}, 501)
