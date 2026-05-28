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
from .trial_question import TrialQuestion, TrialQuestionProgress
from .emergency_mission import EmergencyMissionSession, EmergencyMissionQuestion
from .system_setting import SystemSetting
from .teacher_trial_template import TeacherTrialTemplate
from .system_announcement import SystemAnnouncement
from .student_notification import StudentNotification
from .class_change_request import ClassChangeRequest

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
    'TrialQuestion',
    'TrialQuestionProgress',
    'EmergencyMissionSession',
    'EmergencyMissionQuestion',
    'SystemSetting',
    'TeacherTrialTemplate',
    'SystemAnnouncement',
    'StudentNotification',
    'ClassChangeRequest',
]
