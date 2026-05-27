"""教师试炼题目与学生作答进度"""
import json

from . import db


class TrialQuestion(db.Model):
    """试炼发布时按知识点生成的题目"""

    __tablename__ = 'trial_questions'

    id = db.Column(db.Integer, primary_key=True)
    trial_id = db.Column(db.Integer, db.ForeignKey('trials.id', ondelete='CASCADE'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    stem = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    correct_index = db.Column(db.Integer, nullable=False, default=0)
    knowledge_key = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=db.func.now())

    trial = db.relationship('Trial', backref=db.backref('questions', cascade='all, delete-orphan', lazy=True))
    progress_rows = db.relationship('TrialQuestionProgress', backref='question', cascade='all, delete-orphan')

    def to_dict(self, include_answer=False):
        payload = {
            'id': self.id,
            'trial_id': self.trial_id,
            'sort_order': self.sort_order,
            'stem': self.stem,
            'options': self.options if isinstance(self.options, list) else json.loads(self.options or '[]'),
            'knowledge_key': self.knowledge_key,
        }
        if include_answer:
            payload['correct_index'] = self.correct_index
        return payload


class TrialQuestionProgress(db.Model):
    """学生单题作答状态"""

    __tablename__ = 'trial_question_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(
        db.Integer, db.ForeignKey('trial_questions.id', ondelete='CASCADE'), nullable=False, index=True
    )
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending | completed
    selected_index = db.Column(db.Integer)
    is_correct = db.Column(db.Boolean)
    answered_at = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint('user_id', 'question_id', name='uq_user_trial_question'),)

    user = db.relationship('User', backref='trial_question_progress')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'question_id': self.question_id,
            'status': self.status,
            'selected_index': self.selected_index,
            'is_correct': self.is_correct,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None,
        }
