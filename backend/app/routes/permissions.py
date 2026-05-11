"""权限路由"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.services.permission import PermissionService
from app.utils.response import success_response, error_response

permissions_bp = Blueprint('permissions', __name__, url_prefix='/api/v1')


@permissions_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_roles():
    """获取所有角色"""
    try:
        roles = PermissionService.get_roles()
        return success_response(roles)
    
    except Exception as e:
        return error_response(str(e), 50001)


@permissions_bp.route('/permissions', methods=['GET'])
@jwt_required()
def get_permissions():
    """获取权限列表"""
    try:
        resource = request.args.get('resource')
        permissions = PermissionService.get_permissions(resource)
        return success_response(permissions)
    
    except Exception as e:
        return error_response(str(e), 50001)


@permissions_bp.route('/roles/<int:role_id>/permissions', methods=['POST'])
@jwt_required()
def assign_permissions(role_id):
    """为角色分配权限"""
    try:
        data = request.get_json()
        permission_ids = data.get('permissions', [])
        
        if not permission_ids:
            return error_response('权限列表不能为空', 40001)
        
        PermissionService.assign_permissions_to_role(role_id, permission_ids)
        
        return success_response(None, '权限已更新')
    
    except Exception as e:
        return error_response(str(e), 50001)
