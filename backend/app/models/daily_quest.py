"""每日委托模型"""
from datetime import date, datetime
from . import db


class DailyQuest(db.Model):
    """每日委托定义表"""
    __tablename__ = 'daily_quests'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    period = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    total = db.Column(db.Integer, default=1, nullable=False)
    reward_xp = db.Column(db.Integer, default=0, nullable=False)
    bonus_eligible = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_progress = db.relationship('UserDailyQuest', backref='quest', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'title': self.title,
            'description': self.description,
            'period': self.period,
            'time': self.time,
            'total': self.total,
            'reward_xp': self.reward_xp,
            'bonus_eligible': self.bonus_eligible,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
        }


class UserDailyQuest(db.Model):
    """用户每日委托进度表"""
    __tablename__ = 'user_daily_quests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('daily_quests.id', ondelete='CASCADE'), nullable=False)
    quest_date = db.Column(db.Date, default=date.today, nullable=False)
    current = db.Column(db.Integer, default=0, nullable=False)
    completed_at = db.Column(db.DateTime)
    reward_claimed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'quest_id', 'quest_date', name='unique_user_daily_quest'),
    )

    def to_dict(self):
        quest = self.quest
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quest_id': self.quest_id,
            'quest_date': self.quest_date.isoformat() if self.quest_date else None,
            'key': quest.key if quest else None,
            'title': quest.title if quest else None,
            'description': quest.description if quest else None,
            'period': quest.period if quest else None,
            'time': quest.time if quest else None,
            'total': quest.total if quest else 1,
            'reward_xp': quest.reward_xp if quest else 0,
            'bonus_eligible': quest.bonus_eligible if quest else False,
            'sort_order': quest.sort_order if quest else 0,
            'current': self.current,
            'completed': bool(self.completed_at),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'reward_claimed': bool(self.reward_claimed_at),
            'reward_claimed_at': self.reward_claimed_at.isoformat() if self.reward_claimed_at else None,
        }
