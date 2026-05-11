"""
装饰器集合：权限检查、角色验证等
"""
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import request
from .response import error_response


def role_required(*roles):
    """
    角色验证装饰器

    Usage:
        @role_required('admin', 'teacher')
        def my_view():
            pass
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            # TODO: 从Token中获取role，检查是否在roles列表中
            # 这里先做占位符，实现时从JWT payload中获取
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def permission_required(permission):
    """
    权限验证装饰器

    Usage:
        @permission_required('users:create')
        def create_user():
            pass
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            # TODO: 从Token中获取权限，检查是否有该权限
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
            # TODO: 记录日志
            return error_response(
                str(e),
                50002,
                None,
                500
            )
    return wrapper
