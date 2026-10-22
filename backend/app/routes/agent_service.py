# -*- coding: utf-8 -*-
"""Multi-agent collaboration routes."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.agent_orchestrator import AgentOrchestrator
from app.utils.decorators import role_required
from ..utils.response import error_response, success_response
from ..utils.time import utc_now

agent_bp = Blueprint('agent_service', __name__, url_prefix='/api/v1')


@agent_bp.post('/student/tutor/ask')
@jwt_required()
@role_required('student')
def tutor_ask():
    from app.services.tutoring import TutorService
    return success_response(TutorService.ask(_user_id(), request.get_json(silent=True)))


@agent_bp.get('/student/tutor/turns/<request_id>')
@jwt_required()
@role_required('student')
def tutor_turn(request_id):
    from app.services.tutor_sessions import TutorSessions
    return success_response(TutorSessions.read_turn(_user_id(), request_id))


@agent_bp.post('/student/tutor/turns/<request_id>/cancel')
@jwt_required()
@role_required('student')
def tutor_cancel(request_id):
    from app.services.tutor_runtime import cancel
    return success_response(cancel(_user_id(), request_id))


@agent_bp.get('/student/tutor/usage')
@jwt_required()
@role_required('student')
def tutor_usage():
    from app.services.tutor_runtime import usage
    return success_response(usage(_user_id()))


@agent_bp.get('/ai/usage')
@jwt_required()
@role_required('student','teacher','admin')
def own_model_usage():
    from app.services.model_accounting import summary
    return success_response(summary(_user_id()))


@agent_bp.get('/teacher/classes/<int:class_id>/ai-usage')
@jwt_required()
@role_required('teacher','admin')
def class_model_usage(class_id):
    from app.services.counterexample import owns_class
    from app.services.model_accounting import summary
    owns_class(_user_id(),class_id)
    return success_response(summary(_user_id(),class_id=class_id))


@agent_bp.post('/student/tutor/context')
@jwt_required()
@role_required('student')
def tutor_context():
    from app.services.tutor_context import TutorContextService
    return success_response(TutorContextService.resolve(_user_id(), request.get_json(silent=True)).public())


def _now():
    return utc_now().isoformat() + 'Z'


def _user_id() -> int | None:
    identity = get_jwt_identity()
    if identity is None:
        return None
    return int(identity)


def _student_legacy(body, entry):
    from app.models import db, User
    from app.services.legacy_student_tutoring import LegacyStudentTutoring
    from app.services.tutor_context import TutorContextError
    if not isinstance(body, dict):
        raise TutorContextError('请求体必须是 JSON 对象')
    actor = db.session.get(User, _user_id())
    if actor and actor.role and actor.role.name == 'student':
        return LegacyStudentTutoring.agent(actor.id, body, entry)
    return None


@agent_bp.post('/agents/plan-learning-path')
@jwt_required()
def plan_learning_path():
    body = request.get_json(silent=True) or {}
    user_id = _user_id()
    return success_response(AgentOrchestrator.plan_learning_path(user_id, body))


@agent_bp.post('/agents/student-diagnose')
@jwt_required()
@role_required('student', 'teacher', 'admin')
def student_diagnose():
    body = request.get_json(silent=True)
    user_id = _user_id()
    from app.models import User, db
    from app.services.tutor_context import TutorContextError
    user = db.session.get(User, user_id)
    if user.role.name == 'student':
        from app.services.tutor_compat import TutorCompatibility
        return success_response(TutorCompatibility.ask(user_id, body, 'student-diagnose'))
    if not isinstance(body, dict):
        raise TutorContextError('请求体必须是 JSON 对象')
    code = body.get('code')
    if not isinstance(code, str) or not code.strip():
        return error_response('code required', code=400)
    return success_response(AgentOrchestrator.student_diagnose(user_id, {**body, 'studentId': body.get('studentId') or body.get('student_id') or str(user_id)}))


@agent_bp.post('/agents/diagnose-learning')
@jwt_required()
def diagnose_learning():
    """Diagnose persisted learning evidence for the messenger quick action."""
    legacy = _student_legacy(request.get_json(silent=True), 'diagnose-learning')
    if legacy is not None:
        return success_response(legacy)
    return success_response(AgentOrchestrator.diagnose_learning_overview(_user_id()))


@agent_bp.post('/agents/trial-feedback')
@jwt_required()
@role_required('student')
def trial_feedback():
    return success_response(AgentOrchestrator.trial_feedback(_user_id(), request.get_json(silent=True)))


@agent_bp.post('/agents/messenger-quick-action')
@jwt_required()
def messenger_quick_action():
    body = request.get_json(silent=True) or {}
    action = (body.get('action') or '').strip()
    if not action:
        return error_response('action required', code=400)
    try:
        return success_response(AgentOrchestrator.messenger_quick_action(_user_id(), action))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@agent_bp.post('/agents/code-learning-cycle')
@jwt_required()
@role_required('student')
def code_learning_cycle():
    """Run the sandbox and all student-facing agents as one stable workflow."""
    return success_response(AgentOrchestrator.run_code_learning_cycle(_user_id(), request.get_json(silent=True)))


@agent_bp.post('/agents/trial-coach')
@jwt_required()
@role_required('student')
def trial_coach():
    return success_response(AgentOrchestrator.trial_coach(request.get_json(silent=True), user_id=_user_id()))


@agent_bp.post('/agents/code-hint')
@jwt_required()
@role_required('student')
def code_hint():
    return success_response(AgentOrchestrator.code_hint(_user_id(), request.get_json(silent=True)))


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
    body = request.get_json(silent=True)
    student = _student_legacy(body, 'diagnose')
    if student is not None:
        return success_response(student)
    user_id = _user_id()
    return success_response(AgentOrchestrator.diagnose(user_id, body))


@agent_bp.post('/agent/recommend-path')
@jwt_required()
def recommend_path():
    body = request.get_json(silent=True)
    student = _student_legacy(body, 'recommend-path')
    if student is not None:
        return success_response(student)
    return success_response(AgentOrchestrator.recommend_path({**body, 'user_id': _user_id()}))


@agent_bp.post('/agent/analyze-code')
@jwt_required()
def analyze_code():
    body = request.get_json(silent=True)
    student = _student_legacy(body, 'analyze-code')
    if student is not None:
        return success_response(student)
    code = body.get('code', '')
    if not code.strip():
        return error_response('code required', code=400)
    return success_response(AgentOrchestrator.analyze_code(body))


@agent_bp.post('/agent/generate-feedback')
@jwt_required()
def generate_feedback():
    body = request.get_json(silent=True)
    student = _student_legacy(body, 'generate-feedback')
    if student is not None:
        return success_response(student)
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
