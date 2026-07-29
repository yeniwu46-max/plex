"""控制中枢配置 API"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User, db
from app.services.admin_dashboard import AdminDashboardService
from app.services.learning_resource import LearningResourceService
from app.services.system_setting import SystemSettingService
from app.data.agent_registry import normalize_orchestration, registry_payload
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

admin_settings_bp = Blueprint('admin_settings', __name__, url_prefix='/api/v1/admin')


def _role_name(user_id):
    user = db.session.get(User, int(user_id))
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
        period = request.args.get('period', 'month')
        if period not in ('today', 'week', 'month'):
            period = 'month'
        return success_response(AdminDashboardService.get_dashboard(period))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/trials/teachers', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_trial_teachers():
    try:
        return success_response({'items': AdminDashboardService.list_teachers_with_trials()})
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/trials/teachers/<int:teacher_id>/classes', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_teacher_trial_classes(teacher_id: int):
    try:
        return success_response({'items': AdminDashboardService.list_teacher_classes(teacher_id)})
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/trials/classes/<int:class_id>/stats', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_class_trial_stats(class_id: int):
    try:
        payload = AdminDashboardService.list_class_trial_stats(class_id)
        if not payload:
            return error_response('班级不存在', 40401, None, 404)
        return success_response(payload)
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


@admin_settings_bp.route('/agent-orchestration', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_agent_orchestration():
    try:
        config = SystemSettingService.get_global_orchestration()
        payload = registry_payload(config)
        payload['config'] = config
        return success_response(payload)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/agent-orchestration', methods=['PUT'])
@jwt_required()
@role_required('admin')
def save_agent_orchestration():
    try:
        user_id = int(get_jwt_identity())
        body = request.get_json() or {}
        incoming = {
            'enabled': body.get('enabled', True),
            'grading_agents': body.get('grading_agents') or [],
            'learning_pipeline': body.get('learning_pipeline') or [],
        }
        saved = SystemSettingService.save_global_orchestration(user_id, incoming)
        payload = registry_payload(saved)
        payload['config'] = saved
        return success_response(payload, '智能体编排已保存')
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/learning-resources', methods=['GET'])
@jwt_required()
@role_required('admin', 'teacher')
def list_learning_resources():
    try:
        return success_response(LearningResourceService.list_all(active_only=False))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/learning-resources/import', methods=['POST'])
@jwt_required()
@role_required('admin')
def import_learning_resources():
    try:
        payload = request.get_json() or {}
        return success_response(LearningResourceService.import_json(payload), '资源已导入')
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@admin_settings_bp.route('/backup', methods=['GET'])
@jwt_required()
@role_required('admin')
def admin_backup():
    try:
        return success_response(AdminDashboardService.export_backup_snapshot())
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
