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
from .class_enrollments import class_enrollments_bp
from .uploads import uploads_bp
from .code import code_bp
from .knowledge_base import kb_bp
from .agent_service import agent_bp
from .knowledge_graph import kg_graph_bp
from .search import search_bp
from .file_upload import upload_bp
from .student_profile import student_profile_bp
from .personalized_resources import personalized_resources_bp
from .trial_comments import trial_comments_bp
from .health import health_bp
from .media import media_bp

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
    app.register_blueprint(class_enrollments_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(code_bp)
    app.register_blueprint(kb_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(kg_graph_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(student_profile_bp)
    app.register_blueprint(personalized_resources_bp)
    app.register_blueprint(trial_comments_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(media_bp)
