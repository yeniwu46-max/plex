"""学生站内通知"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.student_notification import StudentNotificationService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

student_notifications_bp = Blueprint('student_notifications', __name__, url_prefix='/api/v1/student')


@student_notifications_bp.route('/notifications', methods=['GET'])
@jwt_required()
@role_required('student')
def list_notifications():
    try:
        user_id = int(get_jwt_identity())
        unread_only = request.args.get('unread_only', '0') in ('1', 'true', 'yes')
        limit = min(request.args.get('limit', 30, type=int), 50)
        items = StudentNotificationService.list_for_user(user_id, unread_only=unread_only, limit=limit)
        unread = StudentNotificationService.list_for_user(user_id, unread_only=True, limit=99)
        return success_response({'items': items, 'unread_count': len(unread)})
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_notifications_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@jwt_required()
@role_required('student')
def mark_notification_read(notification_id):
    try:
        user_id = int(get_jwt_identity())
        row = StudentNotificationService.mark_read(user_id, notification_id)
        return success_response(row)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_notifications_bp.route('/notifications/read-all', methods=['POST'])
@jwt_required()
@role_required('student')
def mark_all_read():
    try:
        user_id = int(get_jwt_identity())
        StudentNotificationService.mark_all_read(user_id)
        return success_response(None, '已全部标为已读')
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
