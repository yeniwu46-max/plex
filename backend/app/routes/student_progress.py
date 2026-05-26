"""学生星轨 / 档案聚合 API"""
from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

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


@student_progress_bp.route('/dashboard-extras', methods=['GET'])
@jwt_required()
@role_required('student')
def get_dashboard_extras():
    try:
        user_id = int(get_jwt_identity())
        return success_response(StudentProgressService.get_student_dashboard_extras(user_id))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
