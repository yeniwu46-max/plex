"""用户成就关联表模型"""
from datetime import datetime
from . import db


class UserAchievement(db.Model):
    """用户成就关联表"""
    __tablename__ = 'user_achievements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id', ondelete='CASCADE'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),)

    def __repr__(self):
        return f'<UserAchievement user_id={self.user_id} achievement_id={self.achievement_id}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'achievement_id': self.achievement_id,
            'achievement': self.achievement.to_dict() if self.achievement else None,
            'unlocked_at': self.unlocked_at.isoformat() if self.unlocked_at else None,
        }
