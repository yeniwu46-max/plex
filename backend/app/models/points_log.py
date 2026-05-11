"""积分日志模型"""
from datetime import datetime
from . import db


class PointsLog(db.Model):
    """积分日志表"""
    __tablename__ = 'points_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100))  # complete_course, daily_task, submission
    related_id = db.Column(db.Integer)  # 关联的课程/任务ID

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PointsLog user_id={self.user_id} points={self.points}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'points': self.points,
            'reason': self.reason,
            'related_id': self.related_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
