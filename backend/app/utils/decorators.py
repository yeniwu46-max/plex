"""
装饰器集合：权限检查、角色验证等
"""
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import request, g
from .response import error_response


def role_required(*roles):
    """
    角色验证装饰器 - 检查用户是否属于指定的角色之一

    Usage:
        @role_required('admin', 'teacher')
        def my_view():
            pass
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            from app.models import User
            user = User.query.get(user_id)

            if not user or not user.role:
                return error_response("用户信息获取失败或未设置角色", 40301, None, 403)

            if user.role.name not in roles:
                return error_response(
                    f"您没有权限执行此操作。需要角色: {', '.join(roles)}，当前角色: {user.role.name}",
                    40301,
                    None,
                    403
                )

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def permission_required(*permissions):
    """
    权限验证装饰器 - 检查用户是否拥有指定的权限

    Usage:
        @permission_required('manage_classes')
        def delete_class():
            pass

        # 支持多个权限（满足其中一个即可）
        @permission_required('manage_users', 'admin')
        def manage():
            pass
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            from app.models import User
            user = User.query.get(user_id)

            if not user or not user.role:
                return error_response("用户信息获取失败或未设置角色", 40301, None, 403)

            # 获取用户的所有权限
            user_permissions = set()
            if user.role and user.role.permissions:
                for perm in user.role.permissions:
                    user_permissions.add(perm.name)

            # 检查是否拥有至少一个所需权限
            required_permissions = set(permissions)
            if not user_permissions & required_permissions:
                return error_response(
                    f"您没有权限执行此操作。需要权限: {', '.join(permissions)}",
                    40301,
                    None,
                    403
                )

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def validate_request_json(required_fields=None):
    """
    请求JSON验证装饰器

    Usage:
        @validate_request_json(['username', 'password'])
        def login():
            pass
    """
    if required_fields is None:
        required_fields = []

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if data is None:
                return error_response("请求体必须是JSON格式", 40004, None, 400)

            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return error_response(
                    f"缺少必需字段: {', '.join(missing_fields)}",
                    40004,
                    None,
                    400
                )

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def handle_exceptions(fn):
    """
    异常处理装饰器

    Usage:
        @handle_exceptions
        def risky_operation():
            pass
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return error_response(
                str(e),
                50002,
                None,
                500
            )
    return wrapper
