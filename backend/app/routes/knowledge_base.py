# -*- coding: utf-8 -*-
"""Knowledge base route - RAG service."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..services.rag_service import RagService
from ..utils.response import error_response, success_response

kb_bp = Blueprint('knowledge_base', __name__, url_prefix='/api/v1')


@kb_bp.post('/kb/upload')
@jwt_required()
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
    result = RagService.query(question)
    return success_response({
        'question': question,
        **result,
        'queried_at': RagService.status()['last_sync'],
    })


@kb_bp.get('/kb/documents')
@jwt_required()
def list_documents():
    return success_response(RagService.list_documents())


@kb_bp.get('/kb/status')
@jwt_required()
def kb_status():
    return success_response(RagService.status())


@kb_bp.post('/kb/parse-document')
@jwt_required()
def parse_document():
    """后续处理 stub：触发知识库解析（第一阶段 pending）。"""
    body = request.get_json(silent=True) or {}
    file_id = body.get('fileId', '')
    return success_response({'status': 'pending', 'fileId': file_id, 'message': 'RAG 解析队列已接收，功能即将开放'})
