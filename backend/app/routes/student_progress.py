"""学生星轨 / 档案聚合 API"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.emergency_mission import EmergencyMissionService
from app.services.student_progress import StudentProgressService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

student_progress_bp = Blueprint('student_progress', __name__, url_prefix='/api/v1/student')


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


@student_progress_bp.route('/dashboard-extras', methods=['GET'])
@jwt_required()
@role_required('student')
def get_dashboard_extras():
    try:
        user_id = int(get_jwt_identity())
        return success_response(StudentProgressService.get_student_dashboard_extras(user_id))
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
