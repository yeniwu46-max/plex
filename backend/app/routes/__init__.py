"""路由初始化"""
from flask import Blueprint
from .auth import auth_bp
from .users import users_bp
from .classes import classes_bp
from .permissions import permissions_bp
from .achievements import achievements_bp
from .daily_quests import daily_quests_bp
from .teacher import teacher_bp
from .trials import trials_bp
from .admin_settings import admin_settings_bp
from .student_progress import student_progress_bp
from .teacher_resources import teacher_resources_bp
from .announcements import announcements_bp
from .student_notifications import student_notifications_bp
from .class_requests import class_requests_bp
from .uploads import uploads_bp
from .code import code_bp
from .knowledge_base import kb_bp
from .agent_service import agent_bp

def register_routes(app):
    """注册所有路由"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(achievements_bp)
    app.register_blueprint(daily_quests_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(trials_bp)
    app.register_blueprint(admin_settings_bp)
    app.register_blueprint(student_progress_bp)
    app.register_blueprint(teacher_resources_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(student_notifications_bp)
    app.register_blueprint(class_requests_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(code_bp)
    app.register_blueprint(kb_bp)
    app.register_blueprint(agent_bp)
