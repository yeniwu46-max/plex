"""系统公告"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User
from app.services.announcement import AnnouncementService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

announcements_bp = Blueprint('announcements', __name__, url_prefix='/api/v1')


def _role_name(user_id: int) -> str:
    user = User.query.get(user_id)
    return user.role.name if user and user.role else ''


@announcements_bp.route('/teacher/announcements', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_teacher_announcements():
    try:
        user_id = int(get_jwt_identity())
        return success_response(AnnouncementService.list_for_role(_role_name(user_id)))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@announcements_bp.route('/admin/announcements', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_admin_announcements():
    try:
        return success_response(AnnouncementService.list_for_role('teacher', limit=50))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@announcements_bp.route('/student/announcements', methods=['GET'])
@jwt_required()
@role_required('student')
def list_student_announcements():
    try:
        return success_response(AnnouncementService.list_for_role('student', limit=20))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@announcements_bp.route('/admin/announcements', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_admin_announcement():
    try:
        admin_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(AnnouncementService.create(admin_id, payload), '公告已发布')
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
