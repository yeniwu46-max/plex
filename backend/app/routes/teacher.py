"""Teacher workspace routes."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.teacher import TeacherService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

teacher_bp = Blueprint('teacher', __name__, url_prefix='/api/v1/teacher')


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
