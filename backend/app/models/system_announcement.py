"""系统公告（管理员 → 教师等）"""
from datetime import datetime

from . import db


class SystemAnnouncement(db.Model):
    __tablename__ = 'system_announcements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    target_role = db.Column(db.String(20), nullable=False, default='teacher')  # teacher | student | all
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[created_by])

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'body': self.body,
            'target_role': self.target_role,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
