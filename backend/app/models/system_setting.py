"""控制中枢 / 平台配置（JSON 文档 per scope）"""
import json
from datetime import datetime

from . import db


class SystemSetting(db.Model):
    """班级或全局系统配置；class_id 为空表示平台默认。"""

    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True, unique=True, index=True)
    payload_json = db.Column(db.Text, nullable=False, default='{}')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class_rel = db.relationship('Class', backref=db.backref('system_setting', uselist=False))
    editor = db.relationship('User', foreign_keys=[updated_by])

    def get_payload(self):
        try:
            return json.loads(self.payload_json or '{}')
        except (TypeError, json.JSONDecodeError):
            return {}

    def set_payload(self, data):
        self.payload_json = json.dumps(data, ensure_ascii=False)

    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.class_id,
            'settings': self.get_payload(),
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
