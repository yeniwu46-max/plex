"""教师试炼作业模板"""
import json
from datetime import datetime

from . import db


class TeacherTrialTemplate(db.Model):
    __tablename__ = 'teacher_trial_templates'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True, index=True)
    title = db.Column(db.String(120), nullable=False)
    trial_type = db.Column(db.String(32), nullable=False, default='solo')
    knowledge_keys_json = db.Column(db.Text, nullable=False, default='[]')
    difficulty = db.Column(db.Integer, default=60)
    duration_minutes = db.Column(db.Integer, default=60)
    reward_points = db.Column(db.Integer, default=35)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = db.relationship('User', backref='trial_templates', foreign_keys=[teacher_id])

    def knowledge_keys(self) -> list[str]:
        try:
            parsed = json.loads(self.knowledge_keys_json or '[]')
            return [str(k) for k in parsed if k]
        except (TypeError, json.JSONDecodeError):
            return []

    def set_knowledge_keys(self, keys: list[str]) -> None:
        self.knowledge_keys_json = json.dumps(keys, ensure_ascii=False)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'class_id': self.class_id,
            'title': self.title,
            'trial_type': self.trial_type,
            'knowledge_keys': self.knowledge_keys(),
            'difficulty': self.difficulty,
            'duration_minutes': self.duration_minutes,
            'reward_points': self.reward_points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
