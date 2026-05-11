"""服务初始化"""
from .auth import AuthService
from .user import UserService
from .class_service import ClassService
from .permission import PermissionService
from .achievement import AchievementService

__all__ = [
    'AuthService',
    'UserService',
    'ClassService',
    'PermissionService',
    'AchievementService',
]
