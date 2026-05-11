"""路由初始化"""
from flask import Blueprint
from .auth import auth_bp
from .users import users_bp
from .classes import classes_bp
from .permissions import permissions_bp
from .achievements import achievements_bp

def register_routes(app):
    """注册所有路由"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(achievements_bp)
