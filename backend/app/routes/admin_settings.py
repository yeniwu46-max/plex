"""控制中枢配置 API"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User
from app.services.admin_dashboard import AdminDashboardService
from app.services.system_setting import SystemSettingService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

admin_settings_bp = Blueprint('admin_settings', __name__, url_prefix='/api/v1/admin')


def _role_name(user_id):
    user = User.query.get(int(user_id))
    return user.role.name if user and user.role else None


@admin_settings_bp.route('/settings', methods=['GET'])
@jwt_required()
@role_required('admin', 'teacher')
def get_admin_settings():
    try:
        user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        return success_response(SystemSettingService.get_settings(user_id, _role_name(user_id), class_id))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_admin_dashboard():
    try:
        return success_response(AdminDashboardService.get_dashboard())
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/settings', methods=['PUT'])
@jwt_required()
@role_required('admin', 'teacher')
def save_admin_settings():
    try:
        user_id = int(get_jwt_identity())
        body = request.get_json() or {}
        class_id = body.get('class_id')
        settings = body.get('settings') if 'settings' in body else {k: v for k, v in body.items() if k != 'class_id'}
        return success_response(
            SystemSettingService.save_settings(user_id, _role_name(user_id), settings, class_id),
            '配置已保存',
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
