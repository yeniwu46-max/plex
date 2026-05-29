"""Teacher workspace routes."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User
from app.services.assignment import AssignmentService
from app.services.teacher import TeacherService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

teacher_bp = Blueprint('teacher', __name__, url_prefix='/api/v1/teacher')


def _role_name(user_id):
    user = User.query.get(int(user_id))
    return user.role.name if user and user.role else None


@teacher_bp.route('/overview', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_teacher_overview():
    """Return the teacher dashboard aggregate for one class."""
    try:
        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        period = request.args.get('period', 'week')
        return success_response(TeacherService.get_overview(current_user_id, class_id, period))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/class-stats', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_teacher_class_stats():
    try:
        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        return success_response(TeacherService.get_class_stats(current_user_id, class_id))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/classes/<int:class_id>/trial-answers', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_class_trial_answers(class_id):
    """班级维度：查看所有试炼的学生作答明细（与学生端提交同步）。"""
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(
            AssignmentService.get_class_answer_board(current_user_id, class_id, _role_name(current_user_id))
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/students/<int:student_id>/trial-answers', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_student_trial_answers(student_id):
    """学生维度：查看某 Explorer 在各试炼中的逐题作答。"""
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(
            AssignmentService.get_student_answer_board(current_user_id, student_id, _role_name(current_user_id))
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
