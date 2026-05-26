"""User routes."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services import UserService
from app.utils.response import success_response, error_response
from app.utils.decorators import permission_required

users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')


def _current_user():
    from app.models import User

    return User.query.get(get_jwt_identity())


def _permission_names(user):
    if not user or not user.role or not user.role.permissions:
        return set()
    return {perm.name for perm in user.role.permissions}


@users_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        current_user_id = int(get_jwt_identity())
        user_info = UserService.get_current_user_info(current_user_id)
        return success_response(user_info)
    except Exception as e:
        return error_response(str(e), 50001)


@users_bp.route('', methods=['POST'])
@jwt_required()
@permission_required('create_user')
def create_user():
    """Create a student account from the admin console."""
    try:
        current_user = _current_user()
        if not current_user or not current_user.role or current_user.role.name != 'admin':
            return error_response('只有管理员可以新增学生', 40301, None, 403)

        data = request.get_json() or {}
        required_fields = ['username', 'email', 'password', 'real_name']
        for field in required_fields:
            if not data.get(field):
                return error_response(f'缺少必需字段: {field}', 40001, None, 400)

        user = UserService.create_student(
            username=data['username'].strip(),
            email=data['email'].strip(),
            password=data['password'],
            real_name=data['real_name'].strip(),
            phone=data.get('phone'),
            gender=data.get('gender'),
            bio=data.get('bio'),
            class_id=data.get('class_id'),
        )
        return success_response(user.to_dict(), '学生创建成功', 0, 201)
    except Exception as e:
        return error_response(str(e), 40001)


@users_bp.route('', methods=['GET'])
@jwt_required()
@permission_required('view_users')
def get_users():
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
            search=search,
        )
        return success_response(result)
    except Exception as e:
        return error_response(str(e), 50001)


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@permission_required('view_users')
def get_user(user_id):
    try:
        user = UserService.get_user(user_id)
        return success_response(user.to_dict())
    except Exception as e:
        return error_response(str(e), 40401)


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        current_user_id = int(get_jwt_identity())
        current_user = _current_user()
        admin_edit = current_user_id != user_id

        if admin_edit:
            if 'edit_user' not in _permission_names(current_user):
                return error_response('您没有权限修改其他用户信息', 40301, None, 403)

        data = request.get_json() or {}
        user = UserService.update_user(user_id, admin_edit=admin_edit, **data)
        return success_response(user.to_dict(), '更新成功')
    except Exception as e:
        return error_response(str(e), 50001)


@users_bp.route('/<int:user_id>/password', methods=['PUT'])
@jwt_required()
def change_password(user_id):
    try:
        current_user_id = int(get_jwt_identity())
        if current_user_id != user_id:
            return error_response('无权修改其他用户密码', 40301, None, 403)

        data = request.get_json() or {}
        if not data.get('old_password') or not data.get('new_password'):
            return error_response('旧密码和新密码不能为空', 40001, None, 400)

        from app.services.auth import AuthService

        AuthService.change_password(
            user_id=user_id,
            old_password=data['old_password'],
            new_password=data['new_password'],
        )
        return success_response(None, '密码修改成功')
    except Exception as e:
        return error_response(str(e), 50001)


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@permission_required('delete_user')
def delete_user(user_id):
    try:
        UserService.delete_user(user_id)
        return success_response(None, '用户已删除')
    except Exception as e:
        return error_response(str(e), 50001)


@users_bp.route('/<int:user_id>/status', methods=['PATCH'])
@jwt_required()
@permission_required('edit_user')
def update_user_status(user_id):
    try:
        data = request.get_json() or {}
        status = data.get('status')

        if status not in ['active', 'frozen']:
            return error_response('无效的状态值', 40001, None, 400)

        if status == 'frozen':
            UserService.freeze_user(user_id)
        else:
            UserService.unfreeze_user(user_id)

        return success_response(None, '用户状态已更新')
    except Exception as e:
        return error_response(str(e), 50001)


@users_bp.route('/<int:user_id>/permissions', methods=['GET'])
@jwt_required()
@permission_required('view_users')
def get_user_permissions(user_id):
    try:
        permissions = UserService.get_user_permissions(user_id)
        return success_response(permissions)
    except Exception as e:
        return error_response(str(e), 50001)
