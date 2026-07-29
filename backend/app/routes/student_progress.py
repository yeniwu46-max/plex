"""学生星轨 / 档案聚合 API"""
from flask import Blueprint, Response, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.emergency_mission import EmergencyMissionService
from app.services.course_safety import CourseSafetyService, SafetyViolation
from app.services.evaluation import EvaluationService
from app.services.learning_resource import LearningResourceService
from app.services.llm_stream import sse_event, sse_headers
from app.services.messenger_chat import MessengerChatService
from app.services.mistake import MistakeService
from app.services.recommendation import RecommendationService
from app.services.presence import PresenceService
from app.services.student_progress import StudentProgressService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

student_progress_bp = Blueprint('student_progress', __name__, url_prefix='/api/v1/student')


@student_progress_bp.route('/overview', methods=['GET'])
@jwt_required()
@role_required('student')
def get_overview():
    try:
        user_id = int(get_jwt_identity())
        return success_response(StudentProgressService.get_overview(user_id))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/learning-path', methods=['GET'])
@jwt_required()
@role_required('student')
def get_learning_path():
    try:
        user_id = int(get_jwt_identity())
        return success_response(StudentProgressService.get_learning_path(user_id))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/archive-insights', methods=['GET'])
@jwt_required()
@role_required('student')
def get_archive_insights():
    try:
        user_id = int(get_jwt_identity())
        return success_response(StudentProgressService.get_archive_insights(user_id))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/emergency-missions/today-status', methods=['GET'])
@jwt_required()
@role_required('student')
def get_emergency_today_status():
    try:
        user_id = int(get_jwt_identity())
        return success_response(EmergencyMissionService.today_status(user_id))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/emergency-missions/start', methods=['POST'])
@jwt_required()
@role_required('student')
def start_emergency_mission():
    try:
        user_id = int(get_jwt_identity())
        return success_response(EmergencyMissionService.start_session(user_id), '紧急任务已生成')
    except ValueError as exc:
        msg = str(exc)
        if msg == 'already_done_today':
            return error_response('今日已完成紧急任务，明日再来吧', 40901, None, 409)
        return error_response(msg, 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/emergency-missions/<int:session_id>/submit', methods=['POST'])
@jwt_required()
@role_required('student')
def submit_emergency_mission(session_id):
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        answers = payload.get('answers')
        if not isinstance(answers, list) or not answers:
            return error_response('answers 不能为空', 40001, None, 400)
        return success_response(
            EmergencyMissionService.submit_session(user_id, session_id, answers),
            '提交成功',
        )
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/emergency-missions/<int:session_id>/explanation', methods=['GET'])
@jwt_required()
@role_required('student')
def get_emergency_mission_explanation(session_id):
    try:
        user_id = int(get_jwt_identity())
        return success_response(EmergencyMissionService.generate_ai_explanation(user_id, session_id))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/dashboard-extras', methods=['GET'])
@jwt_required()
@role_required('student')
def get_dashboard_extras():
    try:
        user_id = int(get_jwt_identity())
        return success_response(StudentProgressService.get_student_dashboard_extras(user_id))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/presence/heartbeat', methods=['POST'])
@jwt_required()
@role_required('student')
def heartbeat_presence():
    try:
        user_id = int(get_jwt_identity())
        return success_response(PresenceService.heartbeat(user_id), '在线状态已更新')
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/ability-stats', methods=['GET'])
@jwt_required()
@role_required('student')
def get_ability_stats():
    try:
        user_id = int(get_jwt_identity())
        return success_response(StudentProgressService.get_ability_stats(user_id))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/mistakes', methods=['GET'])
@jwt_required()
@role_required('student')
def list_student_mistakes():
    try:
        user_id = int(get_jwt_identity())
        knowledge_key = request.args.get('knowledge_key')
        active_only = request.args.get('active_only', 'true').lower() != 'false'
        items = MistakeService.list_for_student(
            user_id,
            knowledge_key=knowledge_key,
            active_only=active_only,
        )
        weak = MistakeService.list_weak_knowledge(user_id)
        return success_response({'items': items, 'weak_knowledge': weak, 'total': len(items)})
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/code-trial/runs', methods=['POST'])
@jwt_required()
@role_required('student')
def record_code_trial_run():
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        row = MistakeService.record_code_trial_run(user_id, payload)
        return success_response({'record': row.to_dict() if row else None})
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/recommendations', methods=['GET'])
@jwt_required()
@role_required('student')
def get_recommendations():
    try:
        user_id = int(get_jwt_identity())
        period = request.args.get('period', '7d')
        return success_response(RecommendationService.get_student_recommendations(user_id, period))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/learning-resources', methods=['GET'])
@jwt_required()
@role_required('student')
def list_learning_resources():
    try:
        knowledge_key = request.args.get('knowledge_key')
        return success_response(LearningResourceService.list_for_knowledge(knowledge_key))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/messenger/chat', methods=['POST'])
@jwt_required()
@role_required('student')
def messenger_chat():
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        message = payload.get('message') or payload.get('content') or ''
        history = payload.get('history') or payload.get('messages') or []
        return success_response(MessengerChatService.chat(user_id, message, history))
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/messenger/chat/stream', methods=['POST'])
@jwt_required()
@role_required('student')
def messenger_chat_stream():
    """SSE 流式驿站对话：逐 token 推送回复，最后推送 done 事件。"""
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    message = (payload.get('message') or payload.get('content') or '').strip()
    history = payload.get('history') or payload.get('messages') or []
    if not message:
        return error_response('消息不能为空', 40001, None, 400)
    try:
        # 安全检查必须在建立流式响应之前完成，违规时返回普通 JSON 错误。
        CourseSafetyService.ensure_safe(message, enforce_course_scope=True)
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)

    def generate():
        try:
            for event in MessengerChatService.chat_stream(user_id, message, history):
                yield sse_event(event)
        except Exception as exc:  # 流中异常只能通过 SSE 帧告知前端
            yield sse_event({'type': 'error', 'message': str(exc)})

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers=sse_headers(),
    )


@student_progress_bp.route('/learning-report', methods=['GET'])
@jwt_required()
@role_required('student')
def get_learning_report():
    try:
        user_id = int(get_jwt_identity())
        period = request.args.get('period', '7d')
        return success_response(EvaluationService.get_student_learning_report(user_id, period))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/learning-report/generate', methods=['POST'])
@jwt_required()
@role_required('student')
def generate_learning_report():
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json(silent=True) or {}
        period = payload.get('period') or request.args.get('period', '7d')
        return success_response(EvaluationService.generate_phase_report(user_id, period))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_progress_bp.route('/learning-effect', methods=['GET'])
@jwt_required()
@role_required('student')
def get_learning_effect():
    try:
        user_id = int(get_jwt_identity())
        task_id = request.args.get('task_id')
        return success_response(EvaluationService.get_learning_effect(user_id, task_id))
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
