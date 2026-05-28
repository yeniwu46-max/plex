"""临时脚本：用正确 UTF-8 重写新增路由文件"""
import os

BASE = os.path.join(os.path.dirname(__file__), 'app', 'routes')

CODE_PY = r'''# -*- coding: utf-8 -*-
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
'''

KB_PY = r'''# -*- coding: utf-8 -*-
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
'''

AGENT_PY = r'''# -*- coding: utf-8 -*-
"""Multi-agent collaboration route - Mock CrewAI first phase."""
import random
from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..utils.response import success_response, error_response

agent_bp = Blueprint('agent_service', __name__, url_prefix='/api/v1')

WEAK_POINTS = [
    'loop boundary', 'recursion base case', 'list slicing',
    'dict key access', 'function return', 'exception handling',
    'string format', 'nested condition',
]

PATHS = {
    'loop': ['variables', 'condition', 'loop', 'list', 'sorting'],
    'recursion': ['function', 'condition', 'recursion', 'dynamic programming'],
    'default': ['variables', 'control flow', 'function', 'data structure'],
}

ERROR_TIPS = {
    'IndexError': 'List index out of range. Check loop bounds against list length.',
    'TypeError': 'Type mismatch. Check you are operating on compatible types.',
    'NameError': 'Variable not defined. Check spelling and assignment order.',
    'SyntaxError': 'Syntax error. Check indentation, brackets, and colons.',
    'ZeroDivisionError': 'Division by zero. Check denominator before dividing.',
}


def _now():
    return datetime.utcnow().isoformat()


@agent_bp.post('/agent/diagnose')
@jwt_required()
def diagnose():
    body = request.get_json(silent=True) or {}
    code_errors = body.get('code_errors', [])
    weak_points = random.sample(WEAK_POINTS, k=min(3, len(WEAK_POINTS)))
    error_types = [{'type': e, 'explanation': ERROR_TIPS[e]} for e in code_errors if e in ERROR_TIPS]
    return success_response({
        'agent': 'DiagnosisAgent', 'status': 'completed',
        'weak_points': weak_points, 'error_types': error_types or [{'type': 'LogicError', 'explanation': 'Logic error detected.'}],
        'overall_assessment': 'Found {} weak points, focus on: {}'.format(len(weak_points), weak_points[0]),
        'diagnosed_at': _now(),
    })


@agent_bp.post('/agent/recommend-path')
@jwt_required()
def recommend_path():
    body = request.get_json(silent=True) or {}
    weak_points = body.get('weak_points', [])
    keyword = weak_points[0] if weak_points else 'default'
    match_key = next((k for k in PATHS if k in keyword), 'default')
    path_nodes = PATHS[match_key]
    steps = [{'step': i+1, 'node': n, 'action': 'review' if i == 0 else 'practice'} for i, n in enumerate(path_nodes)]
    return success_response({
        'agent': 'PathPlannerAgent', 'status': 'completed',
        'path': {'title': 'Path for: ' + keyword, 'steps': steps, 'total_nodes': len(steps)},
        'confidence': round(0.75 + random.random() * 0.2, 2),
        'recommended_at': _now(),
    })


@agent_bp.post('/agent/analyze-code')
@jwt_required()
def analyze_code():
    body = request.get_json(silent=True) or {}
    code = body.get('code', '')
    error_message = body.get('error_message', '')
    if not code.strip():
        return error_response('code required', code=400)
    error_type = next((k for k in ERROR_TIPS if k.lower() in (code + error_message).lower()), '')
    return success_response({
        'agent': 'CodeAnalyzerAgent', 'status': 'completed',
        'error_type': error_type,
        'explanation': ERROR_TIPS.get(error_type, 'Code structure seems OK, check boundary conditions.'),
        'suggestions': ['Check loop boundary', 'Validate input before use', 'Use print() to debug'],
        'analyzed_at': _now(),
    })


@agent_bp.post('/agent/generate-feedback')
@jwt_required()
def generate_feedback():
    body = request.get_json(silent=True) or {}
    diagnosis = body.get('diagnosis', {})
    weak_points = diagnosis.get('weak_points', ['loop boundary'])
    point = weak_points[0] if weak_points else 'code logic'
    encouragements = [
        'Great first step! Keep going!',
        'Every mistake is a chance to learn!',
        'Your logic is on the right track, just fix the boundary!',
    ]
    return success_response({
        'agent': 'FeedbackGeneratorAgent', 'status': 'completed',
        'feedback': {
            'summary': 'Need to strengthen: ' + point,
            'encouragement': random.choice(encouragements),
            'next_action': 'Complete targeted exercises for: ' + point,
        },
        'generated_at': _now(),
    })


@agent_bp.post('/agent/teacher-suggestion')
@jwt_required()
def teacher_suggestion():
    weak_topics = ['loop boundary', 'recursion', 'list ops']
    risk_count = random.randint(2, 5)
    return success_response({
        'agent': 'TeacherAssistantAgent', 'status': 'completed',
        'class_overview': {
            'active_students': random.randint(15, 28),
            'avg_accuracy': round(0.65 + random.random() * 0.2, 2),
            'weak_topics': weak_topics, 'risk_students_count': risk_count,
        },
        'suggestions': [
            {'priority': 'high', 'type': 'lecture', 'content': 'Focus on: ' + weak_topics[0]},
            {'priority': 'medium', 'type': 'tutoring', 'content': str(risk_count) + ' students need follow-up'},
        ],
        'generated_at': _now(),
    })


@agent_bp.get('/agent/status')
@jwt_required()
def agent_status():
    agents = [
        {'id': 'diagnose', 'name': 'DiagnosisAgent', 'status': 'idle', 'calls_today': random.randint(5, 50)},
        {'id': 'path', 'name': 'PathPlannerAgent', 'status': 'idle', 'calls_today': random.randint(5, 50)},
        {'id': 'code', 'name': 'CodeAnalyzerAgent', 'status': 'idle', 'calls_today': random.randint(5, 50)},
        {'id': 'feedback', 'name': 'FeedbackGeneratorAgent', 'status': 'idle', 'calls_today': random.randint(5, 50)},
        {'id': 'teacher', 'name': 'TeacherAssistantAgent', 'status': 'idle', 'calls_today': random.randint(2, 20)},
    ]
    return success_response({
        'service': 'plex-agent-service', 'version': '0.1.0-mock',
        'agents': agents, 'checked_at': _now(),
    })
'''

files = {'code.py': CODE_PY, 'knowledge_base.py': KB_PY, 'agent_service.py': AGENT_PY}
for fname, content in files.items():
    path = os.path.join(BASE, fname)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f'Written: {fname} ({len(content)} bytes)')

print('All done.')
