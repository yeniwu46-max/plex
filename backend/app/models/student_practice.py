"""Owned practice evidence, favorites and durable six-question exam attempts."""
from .base import db
from app.utils.time import utc_now


class PracticeAttempt(db.Model):
    __tablename__ = 'student_practice_attempts'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    question_ref = db.Column(db.String(100), nullable=False, index=True)
    question_version = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    code = db.Column(db.Text, nullable=False)
    result = db.Column(db.JSON, nullable=False)
    source = db.Column(db.String(32), nullable=False, default='practice')
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self):
        return {k: getattr(self, k) for k in ('id', 'question_ref', 'question_version', 'title', 'code', 'result', 'source')} | {'created_at': self.created_at.isoformat() + 'Z'}


class QuestionFavorite(db.Model):
    __tablename__ = 'student_question_favorites'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    question_ref = db.Column(db.String(100), primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class MockExam(db.Model):
    __tablename__ = 'student_mock_exams'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # Nullable unique slot: one open exam per account, many completed attempts.
    active_user_id = db.Column(db.Integer, unique=True)
    status = db.Column(db.String(24), nullable=False, default='active', index=True)
    questions = db.Column(db.JSON, nullable=False)
    answers = db.Column(db.JSON, nullable=False, default=dict)
    results = db.Column(db.JSON, nullable=False, default=dict)
    revision = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    deadline = db.Column(db.DateTime, nullable=False)
    submitted_at = db.Column(db.DateTime)
    lease_until = db.Column(db.DateTime)
    score = db.Column(db.Float)
