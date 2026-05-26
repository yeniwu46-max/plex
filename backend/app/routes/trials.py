"""试炼路由"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User
from app.services.trial import TrialService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

trials_bp = Blueprint('trials', __name__, url_prefix='/api/v1')


def _role_name(user_id):
    user = User.query.get(int(user_id))
    return user.role.name if user and user.role else None


@trials_bp.route('/teacher/trials', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_teacher_trials():
    try:
        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        if not class_id:
            return error_response('class_id 不能为空', 40001, None, 400)
        return success_response(
            TrialService.list_teacher_trials(current_user_id, class_id, _role_name(current_user_id))
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/teacher/trials', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def create_teacher_trial():
    try:
        current_user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(
            TrialService.create_trial(current_user_id, _role_name(current_user_id), payload),
            '试炼已创建',
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/teacher/trials/<int:trial_id>/publish', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def publish_teacher_trial(trial_id):
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(
            TrialService.publish_trial(current_user_id, trial_id, _role_name(current_user_id)),
            '试炼已发布',
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/teacher/trials/<int:trial_id>', methods=['PATCH'])
@jwt_required()
@role_required('teacher', 'admin')
def update_teacher_trial(trial_id):
    try:
        current_user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(
            TrialService.update_trial(current_user_id, trial_id, _role_name(current_user_id), payload),
            '试炼已更新',
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/student/trials/arena', methods=['GET'])
@jwt_required()
@role_required('student')
def list_student_arena_trials():
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(TrialService.list_student_arena_trials(current_user_id))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/student/trials', methods=['GET'])
@jwt_required()
@role_required('student')
def list_student_trials():
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(TrialService.list_student_trials(current_user_id))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/student/trials/<int:trial_id>/join', methods=['POST'])
@jwt_required()
@role_required('student')
def join_student_trial(trial_id):
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(TrialService.join_trial(current_user_id, trial_id), '已参与试炼')
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/teacher/students/<int:student_id>/trials', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_student_trials_for_teacher(student_id):
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(
            TrialService.list_student_trials_for_teacher(
                current_user_id, student_id, _role_name(current_user_id)
            )
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trials_bp.route('/student/trials/<int:trial_id>/complete', methods=['POST'])
@jwt_required()
@role_required('student')
def complete_student_trial(trial_id):
    try:
        current_user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        score = payload.get('score')
        return success_response(
            TrialService.complete_trial(current_user_id, trial_id, score),
            '试炼已完成',
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
