# -*- coding: utf-8 -*-
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
