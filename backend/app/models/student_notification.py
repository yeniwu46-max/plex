"""学生站内通知（教师发布作业等）"""
from .base import BaseModel, db


class StudentNotification(BaseModel):
    __tablename__ = 'student_notifications'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    kind = db.Column(db.String(32), nullable=False, default='teacher_task_published')
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    trial_id = db.Column(db.Integer, db.ForeignKey('trials.id'), nullable=True, index=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship('User', backref=db.backref('inbox_notifications', lazy='dynamic'))
    trial = db.relationship('Trial', backref=db.backref('student_notifications', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'kind': self.kind,
            'title': self.title,
            'body': self.body,
            'trial_id': self.trial_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
