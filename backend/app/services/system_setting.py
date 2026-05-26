"""控制中枢配置读写"""
import copy

from app.models import Class, SystemSetting, User, db

from .base import BaseService

DEFAULT_SETTINGS = {
    'rules': {
        'open_time': '08-22',
        'daily_limit': '3',
        'difficulty': 48,
        'punish': 'none',
    },
    'data_scope': 'teacher',
    'ai_strategies': [
        {'key': 'recommend', 'enabled': True},
        {'key': 'difficulty', 'enabled': True},
        {'key': 'risk', 'enabled': True},
        {'key': 'rhythm', 'enabled': True},
    ],
    'notices': [
        {'key': 'done', 'enabled': True},
        {'key': 'abyss', 'enabled': True},
        {'key': 'ai', 'enabled': True},
        {'key': 'system', 'enabled': False},
    ],
    'channels': {
        'inbox': True,
        'email': False,
        'wechat': False,
        'sms': False,
    },
}


class SystemSettingService(BaseService):
    @staticmethod
    def _merge_defaults(payload):
        base = copy.deepcopy(DEFAULT_SETTINGS)
        if not payload:
            return base
        for key, value in payload.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = {**base[key], **value}
            else:
                base[key] = value
        return base

    @staticmethod
    def _assert_class_access(class_id, user_id, role_name):
        if role_name == 'admin':
            return
        if not class_id:
            raise PermissionError('仅管理员可修改全局默认配置')
        cls = Class.query.get(class_id)
        if not cls:
            raise ValueError('班级不存在')
        if cls.teacher_id != user_id:
            raise PermissionError('不能修改非本人负责班级的配置')

    @staticmethod
    def get_settings(user_id, role_name, class_id=None):
        if role_name == 'teacher' and not class_id:
            cls = Class.query.filter_by(teacher_id=user_id).first()
            class_id = cls.id if cls else None
        if role_name == 'teacher' and class_id:
            SystemSettingService._assert_class_access(class_id, user_id, role_name)

        row = None
        if class_id:
            row = SystemSetting.query.filter_by(class_id=class_id).first()
        if not row:
            row = SystemSetting.query.filter_by(class_id=None).first()

        settings = SystemSettingService._merge_defaults(row.get_payload() if row else {})
        return {
            'class_id': class_id,
            'scope_class_id': row.class_id if row else None,
            'settings': settings,
            'updated_at': row.updated_at.isoformat() if row and row.updated_at else None,
        }

    @staticmethod
    def save_settings(user_id, role_name, payload, class_id=None):
        SystemSettingService._assert_class_access(class_id, user_id, role_name)
        if role_name == 'teacher' and not class_id:
            cls = Class.query.filter_by(teacher_id=user_id).first()
            if not cls:
                raise ValueError('当前教师没有负责班级')
            class_id = cls.id

        row = SystemSetting.query.filter_by(class_id=class_id).first()
        if not row:
            row = SystemSetting(class_id=class_id)
            db.session.add(row)

        merged = SystemSettingService._merge_defaults(row.get_payload())
        for key, value in (payload or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value

        row.set_payload(merged)
        row.updated_by = user_id
        db.session.commit()
        return SystemSettingService.get_settings(user_id, role_name, class_id)
