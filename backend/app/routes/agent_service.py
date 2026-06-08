# -*- coding: utf-8 -*-
"""Multi-agent collaboration routes."""
from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.agent_orchestrator import AgentOrchestrator
from ..utils.response import error_response, success_response

agent_bp = Blueprint('agent_service', __name__, url_prefix='/api/v1')


def _now():
    return datetime.utcnow().isoformat() + 'Z'


def _user_id() -> int | None:
    identity = get_jwt_identity()
    if identity is None:
        return None
    return int(identity)


@agent_bp.post('/agents/student-diagnose')
@jwt_required()
def student_diagnose():
    body = request.get_json(silent=True) or {}
    code = (body.get('code') or '').strip()
    if not code:
        return error_response('code required', code=400)
    user_id = _user_id()
    student_id = body.get('studentId') or body.get('student_id')
    payload = {
        **body,
        'studentId': student_id or str(user_id),
    }
    return success_response(AgentOrchestrator.student_diagnose(user_id, payload))


@agent_bp.post('/agents/teacher-suggestion')
@jwt_required()
def agents_teacher_suggestion():
    body = request.get_json(silent=True) or {}
    user_id = _user_id()
    return success_response(AgentOrchestrator.teacher_suggestion(user_id, body))


@agent_bp.get('/agents/status')
@jwt_required()
def agents_status():
    status = AgentOrchestrator.agents_status()
    return success_response({
        **status,
        'service': 'plex-agent-service',
        'version': '1.0.0',
        'checked_at': _now(),
    })


# ---- 兼容旧版端点 ----

@agent_bp.post('/agent/diagnose')
@jwt_required()
def diagnose():
    body = request.get_json(silent=True) or {}
    user_id = _user_id()
    return success_response(AgentOrchestrator.diagnose(user_id, body))


@agent_bp.post('/agent/recommend-path')
@jwt_required()
def recommend_path():
    body = request.get_json(silent=True) or {}
    return success_response(AgentOrchestrator.recommend_path(body))


@agent_bp.post('/agent/analyze-code')
@jwt_required()
def analyze_code():
    body = request.get_json(silent=True) or {}
    code = body.get('code', '')
    if not code.strip():
        return error_response('code required', code=400)
    return success_response(AgentOrchestrator.analyze_code(body))


@agent_bp.post('/agent/generate-feedback')
@jwt_required()
def generate_feedback():
    body = request.get_json(silent=True) or {}
    return success_response(AgentOrchestrator.generate_feedback(body))


@agent_bp.post('/agent/teacher-suggestion')
@jwt_required()
def teacher_suggestion_legacy():
    body = request.get_json(silent=True) or {}
    user_id = _user_id()
    legacy = AgentOrchestrator.teacher_suggestion(user_id, body)
    return success_response({
        'agent': 'TeacherAssistantAgent',
        'status': 'completed',
        'class_overview': {
            'active_students': 0,
            'avg_accuracy': 0,
            'weak_topics': [
                w.get('knowledgePoint', '')
                for w in body.get('weakPointStats', [])
            ],
            'risk_students_count': len(legacy.get('interventionGroups', [])),
        },
        'suggestions': [
            {'priority': 'high', 'type': 'lecture', 'content': s}
            for s in legacy.get('teachingSuggestions', [])
        ],
        'teacher': legacy,
        'generated_at': legacy.get('generatedAt'),
        'backend': legacy.get('backend'),
    })


@agent_bp.get('/agent/status')
@jwt_required()
def agent_status_legacy():
    status = AgentOrchestrator.agents_status()
    agents = [
        {
            'id': a['id'],
            'name': a['name'],
            'status': a['status'],
            'calls_today': 0,
            'avgLatency': a.get('avgLatency'),
            'lastRunAt': a.get('lastRunAt'),
        }
        for a in status['agents']
    ]
    return success_response({
        'service': 'plex-agent-service',
        'version': '1.0.0',
        'backend': status['backend'],
        'agents': agents,
        'checked_at': _now(),
    })
