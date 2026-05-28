# -*- coding: utf-8 -*-
"""Knowledge base route - Mock RAGFlow first phase."""
from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..utils.response import success_response, error_response

kb_bp = Blueprint('knowledge_base', __name__, url_prefix='/api/v1')

MOCK_DOCUMENTS = [
    {'id': 'doc_001', 'name': 'Python-basics.pdf', 'size': 2048576,
     'type': 'pdf', 'status': 'indexed', 'chunk_count': 128,
     'uploaded_at': '2026-05-20T10:30:00', 'uploader': 'teacher001'},
    {'id': 'doc_002', 'name': 'Algorithm-slides.pptx', 'size': 5242880,
     'type': 'pptx', 'status': 'indexed', 'chunk_count': 256,
     'uploaded_at': '2026-05-22T14:15:00', 'uploader': 'teacher001'},
    {'id': 'doc_003', 'name': 'DataStruct-exercises.docx', 'size': 1048576,
     'type': 'docx', 'status': 'processing', 'chunk_count': 0,
     'uploaded_at': '2026-05-28T09:00:00', 'uploader': 'teacher001'},
]

MOCK_QA = {
    'loop': 'for loop and while loop are two basic loop structures. Pay attention to boundary conditions to avoid infinite loops.',
    'recursion': 'Recursion is a technique where a function calls itself. Requires: 1) base case; 2) recursive case with smaller problem.',
    'sort': 'Common sorting algorithms: bubble O(n^2), quick O(nlogn), merge O(nlogn). Python built-in sorted() uses Timsort.',
    'list': 'List is the most common data structure in Python. Supports append(), insert(), remove(), pop(), sort(), slicing, etc.',
}

DEFAULT_ANSWER = 'Based on the course knowledge base, this topic relates to core computational thinking concepts. Please refer to the relevant textbook chapters for details.'


@kb_bp.post('/kb/upload')
@jwt_required()
def upload_document():
    file = request.files.get('file')
    if not file or not file.filename:
        return error_response('file required', code=400)
    task_id = 'task_' + datetime.utcnow().strftime('%Y%m%d%H%M%S')
    return success_response({
        'task_id': task_id, 'filename': file.filename,
        'status': 'processing', 'estimated_time': '30s',
    })


@kb_bp.post('/kb/query')
@jwt_required()
def query_knowledge():
    body = request.get_json(silent=True) or {}
    question = body.get('question', '').strip()
    if not question:
        return error_response('question required', code=400)
    answer = DEFAULT_ANSWER
    sources = []
    for keyword, ans in MOCK_QA.items():
        if keyword.lower() in question.lower():
            answer = ans
            sources = [{'doc_id': 'doc_001', 'score': 0.92}]
            break
    return success_response({
        'question': question, 'answer': answer, 'sources': sources,
        'model': 'ragflow-mock-v1',
        'retrieved_at': datetime.utcnow().isoformat(),
    })


@kb_bp.get('/kb/documents')
@jwt_required()
def list_documents():
    status_filter = request.args.get('status')
    docs = MOCK_DOCUMENTS
    if status_filter:
        docs = [d for d in docs if d['status'] == status_filter]
    return success_response({
        'documents': docs, 'total': len(docs),
        'indexed_count': sum(1 for d in MOCK_DOCUMENTS if d['status'] == 'indexed'),
    })


@kb_bp.get('/kb/status')
@jwt_required()
def kb_status():
    return success_response({
        'service': 'ragflow-mock', 'status': 'running',
        'documents_total': len(MOCK_DOCUMENTS),
        'last_sync': datetime.utcnow().isoformat(),
        'note': 'phase-1 mock, will connect RAGFlow later',
    })
