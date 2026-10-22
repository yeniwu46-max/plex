"""
错误处理中间件
"""
from flask import Flask
from flask_jwt_extended import JWTManager
from app.utils import error_response


def register_error_handlers(app: Flask, jwt: JWTManager):
    """
    注册全局错误处理器

    Args:
        app: Flask应用实例
        jwt: JWT管理器实例
    """

    from app.services.execution_errors import ExecutionInputError, ExecutionUnavailable
    from app.services.tutor_context import TutorContextError
    from app.services.counterexample_contract import CounterexampleError

    @app.errorhandler(CounterexampleError)
    def counterexample_error(error):
        from app.models import db
        db.session.rollback()
        return error_response(str(error), error.status * 100 + 1, None, error.status)

    from app.services.rag_runtime import RagRuntimeError

    @app.errorhandler(RagRuntimeError)
    def rag_runtime_error(error):
        from app.models import db
        db.session.rollback()
        return error_response(str(error), error.status * 100 + 1, {'reason': error.reason}, error.status)

    @app.errorhandler(TutorContextError)
    def tutor_context_error(error):
        from app.models import db
        db.session.rollback()
        return error_response(str(error), error.status * 100 + 1, None, error.status)

    @app.errorhandler(ExecutionUnavailable)
    def execution_unavailable(error):
        from app.models import db
        db.session.rollback()
        return error_response(str(error), 50301, {
            'retryable': True, 'reason': error.reason, 'graded': False,
        }, 503)

    @app.errorhandler(ExecutionInputError)
    def execution_input_error(error):
        return error_response(str(error), 40001, None, 400)

    @app.errorhandler(400)
    def bad_request(error):
        """处理400错误"""
        return error_response("请求参数错误", 40004, None, 400)

    @app.errorhandler(401)
    def unauthorized(error):
        """处理401错误"""
        return error_response("未授权，请先登录", 40101, None, 401)

    @app.errorhandler(403)
    def forbidden(error):
        """处理403错误"""
        return error_response("禁止访问，无操作权限", 40301, None, 403)

    @app.errorhandler(404)
    def not_found(error):
        """处理404错误"""
        return error_response("请求的资源不存在", 40401, None, 404)

    @app.errorhandler(500)
    def internal_error(error):
        """处理500错误"""
        return error_response("服务器内部错误", 50002, None, 500)

    # JWT错误处理
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_data):
        return error_response('登录状态已失效，请重新登录', 40101, None, 401)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        """Token过期处理"""
        return error_response("Token已过期，请重新登录", 40101, None, 401)

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """无效Token处理"""
        return error_response("无效的Token", 40101, None, 401)

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """缺少Token处理"""
        return error_response("缺少认证Token", 40101, None, 401)
