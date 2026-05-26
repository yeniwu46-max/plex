"""试炼业务模型"""
from datetime import datetime

from . import db


class Trial(db.Model):
    """班级试炼定义"""

    __tablename__ = 'trials'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    trial_type = db.Column(db.String(32), nullable=False, default='solo')
    knowledge_key = db.Column(db.String(32))
    difficulty = db.Column(db.Integer, default=50)
    duration_minutes = db.Column(db.Integer, default=60)
    status = db.Column(db.String(20), nullable=False, default='running')  # draft | scheduled | running | ended
    reward_points = db.Column(db.Integer, default=35)
    starts_at = db.Column(db.DateTime, default=datetime.utcnow)
    ends_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class_rel = db.relationship('Class', backref='trials')
    teacher = db.relationship('User', backref='created_trials', foreign_keys=[teacher_id])
    participations = db.relationship('TrialParticipation', backref='trial', cascade='all, delete-orphan')

    def to_dict(self, include_stats=False, effective_status=None):
        display_status = effective_status or self.status
        payload = {
            'id': self.id,
            'class_id': self.class_id,
            'teacher_id': self.teacher_id,
            'title': self.title,
            'trial_type': self.trial_type,
            'knowledge_key': self.knowledge_key,
            'difficulty': self.difficulty,
            'duration_minutes': self.duration_minutes,
            'status': self.status,
            'effective_status': display_status,
            'reward_points': self.reward_points,
            'starts_at': self.starts_at.isoformat() if self.starts_at else None,
            'ends_at': self.ends_at.isoformat() if self.ends_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_stats:
            joined = [p for p in self.participations if p.status in ('joined', 'completed')]
            completed = [p for p in self.participations if p.status == 'completed']
            total = len(joined) + len([p for p in self.participations if p.status == 'abandoned'])
            participant_count = len({p.user_id for p in self.participations})
            completion_rate = round((len(completed) / participant_count) * 100) if participant_count else 0
            payload['participant_count'] = participant_count
            payload['completed_count'] = len(completed)
            payload['completion_rate'] = completion_rate
            payload['progress'] = (
                completion_rate
                if display_status == 'running'
                else (100 if display_status == 'ended' else 0)
            )
        return payload


class TrialParticipation(db.Model):
    """学生试炼参与记录"""

    __tablename__ = 'trial_participations'

    id = db.Column(db.Integer, primary_key=True)
    trial_id = db.Column(db.Integer, db.ForeignKey('trials.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='joined')  # joined | completed | abandoned
    score = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint('trial_id', 'user_id', name='unique_trial_user'),)

    user = db.relationship('User', backref='trial_participations')

    def to_dict(self):
        return {
            'id': self.id,
            'trial_id': self.trial_id,
            'user_id': self.user_id,
            'status': self.status,
            'score': self.score,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
