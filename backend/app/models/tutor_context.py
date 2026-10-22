"""Owned execution references for tutoring; self-tests are never assessment events."""
from . import db
from .learner_state import TIMESTAMP
from app.utils.time import utc_now


class TutorCodeRun(db.Model):
    __tablename__ = 'tutor_code_runs'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    question_ref = db.Column(db.String(100))
    question_version = db.Column(db.String(64))
    code_hash = db.Column(db.String(64), nullable=False)
    normalized_code_hash = db.Column(db.String(64), nullable=False)
    execution_kind = db.Column(db.String(20), nullable=False)
    backend = db.Column(db.String(32), nullable=False)
    result = db.Column(db.JSON, nullable=False)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now, index=True)
