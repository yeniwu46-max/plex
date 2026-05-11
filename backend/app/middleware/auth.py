"""JWT认证中间件"""
from flask_jwt_extended import verify_jwt_in_request
from functools import wraps


def token_required(fn):
    """
    Token验证装饰器
    确保请求包含有效的JWT Token

    Usage:
        @app.route('/protected')
        @token_required
        def protected_route():
            pass
    """
    @wraps(fn)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return decorator
