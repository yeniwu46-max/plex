"""数据库模型"""
from .base import BaseModel, db

from .user import User
from .role import Role
from .permission import Permission
from .role_permission import role_permissions
from .class_model import Class
from .achievement import Achievement
from .user_achievement import UserAchievement
from .points_log import PointsLog
from .ranking_cache import RankingCache
from .daily_quest import DailyQuest, UserDailyQuest
from .trial import Trial, TrialParticipation
from .system_setting import SystemSetting

__all__ = [
    'db',
    'BaseModel',
    'User',
    'Role',
    'Permission',
    'role_permissions',
    'Class',
    'Achievement',
    'UserAchievement',
    'PointsLog',
    'RankingCache',
    'DailyQuest',
    'UserDailyQuest',
    'Trial',
    'TrialParticipation',
    'SystemSetting',
]
