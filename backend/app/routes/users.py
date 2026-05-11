"""用户路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import UserService
from app.utils.response import success_response, error_response

users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')


@users_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前用户信息"""
    try:
        current_user_id = get_jwt_identity()
        user_info = UserService.get_current_user_info(current_user_id)
        return success_response(user_info)
    
    except Exception as e:
        return error_response(50001, str(e))


@users_bp.route('', methods=['GET'])
@jwt_required()
def get_users():
    """获取用户列表"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        role = request.args.get('role')
        class_id = request.args.get('class_id', type=int)
        status = request.args.get('status')
        search = request.args.get('search')
        
        result = UserService.get_users_list(
            page=page,
            limit=limit,
            role=role,
            class_id=class_id,
            status=status,
            search=search
        )
        
        return success_response(result)
    
    except Exception as e:
        return error_response(50001, str(e))


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """获取用户信息"""
    try:
        user = UserService.get_user(user_id)
        return success_response(user.to_dict())
    
    except Exception as e:
        return error_response(40401, str(e))


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """更新用户信息"""
    try:
        current_user_id = get_jwt_identity()
        
        # 用户只能修改自己的信息，或者管理员可以修改任何用户
        # 这里简化处理，只允许修改自己的信息
        if current_user_id != user_id:
            return error_response(40301, '无权限修改其他用户信息')
        
        data = request.get_json()
        user = UserService.update_user(user_id, **data)
        
        return success_response(user.to_dict(), '更新成功')
    
    except Exception as e:
        return error_response(50001, str(e))


@users_bp.route('/<int:user_id>/password', methods=['PUT'])
@jwt_required()
def change_password(user_id):
    """修改密码"""
    try:
        current_user_id = get_jwt_identity()
        
        if current_user_id != user_id:
            return error_response(40301, '无权限修改其他用户密码')
        
        data = request.get_json()
        
        if not data.get('old_password') or not data.get('new_password'):
            return error_response(40001, '旧密码和新密码不能为空')
        
        from app.services.auth import AuthService
        AuthService.change_password(
            user_id=user_id,
            old_password=data['old_password'],
            new_password=data['new_password']
        )
        
        return success_response(None, '密码修改成功')
    
    except Exception as e:
        return error_response(50001, str(e))


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """删除用户"""
    try:
        UserService.delete_user(user_id)
        return success_response(None, '用户已删除')
    
    except Exception as e:
        return error_response(50001, str(e))


@users_bp.route('/<int:user_id>/status', methods=['PATCH'])
@jwt_required()
def update_user_status(user_id):
    """更新用户状态"""
    try:
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['active', 'frozen']:
            return error_response(40001, '无效的状态值')
        
        if status == 'frozen':
            UserService.freeze_user(user_id)
        else:
            UserService.unfreeze_user(user_id)
        
        return success_response(None, '用户状态已更新')
    
    except Exception as e:
        return error_response(50001, str(e))


@users_bp.route('/<int:user_id>/permissions', methods=['GET'])
@jwt_required()
def get_user_permissions(user_id):
    """获取用户权限"""
    try:
        permissions = UserService.get_user_permissions(user_id)
        return success_response(permissions)
    
    except Exception as e:
        return error_response(50001, str(e))
