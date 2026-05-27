"""边界条件补给站 · 紧急任务"""
import json

from . import db


class EmergencyMissionSession(db.Model):
    __tablename__ = 'emergency_mission_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    focus_knowledge_key = db.Column(db.String(32), nullable=False, default='algo')
    focus_label = db.Column(db.String(64))
    status = db.Column(db.String(20), nullable=False, default='in_progress')  # in_progress | submitted
    correct_count = db.Column(db.Integer, default=0)
    all_correct = db.Column(db.Boolean, default=False)
    reward_points = db.Column(db.Integer, default=0)
    reward_granted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    submitted_at = db.Column(db.DateTime)

    user = db.relationship('User', backref=db.backref('emergency_missions', lazy=True))
    questions = db.relationship(
        'EmergencyMissionQuestion',
        backref='session',
        cascade='all, delete-orphan',
        order_by='EmergencyMissionQuestion.sort_order',
    )

    def to_dict(self, include_questions=False, reveal_answers=False):
        payload = {
            'id': self.id,
            'focus_knowledge_key': self.focus_knowledge_key,
            'focus_label': self.focus_label,
            'status': self.status,
            'correct_count': self.correct_count,
            'all_correct': self.all_correct,
            'reward_points': self.reward_points,
            'reward_granted': self.reward_granted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
        }
        if include_questions:
            payload['questions'] = [
                q.to_dict(reveal_answer=reveal_answers) for q in self.questions
            ]
        return payload


class EmergencyMissionQuestion(db.Model):
    __tablename__ = 'emergency_mission_questions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey('emergency_mission_sessions.id', ondelete='CASCADE'), nullable=False, index=True
    )
    sort_order = db.Column(db.Integer, nullable=False, default=1)
    stem = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    correct_index = db.Column(db.Integer, nullable=False, default=0)
    knowledge_key = db.Column(db.String(32))
    selected_index = db.Column(db.Integer)
    is_correct = db.Column(db.Boolean)

    def to_dict(self, reveal_answer=False):
        options = self.options if isinstance(self.options, list) else json.loads(self.options or '[]')
        payload = {
            'id': self.id,
            'sort_order': self.sort_order,
            'stem': self.stem,
            'options': options,
            'knowledge_key': self.knowledge_key,
            'selected_index': self.selected_index,
            'is_correct': self.is_correct,
        }
        if reveal_answer:
            payload['correct_index'] = self.correct_index
        return payload
