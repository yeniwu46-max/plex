"""Private task-scoped tutoring history. Only validated output is persisted."""
from . import db
from .learner_state import TIMESTAMP
from app.utils.time import utc_now


class TutorSession(db.Model):
    __tablename__ = 'tutor_sessions'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # Frozen at creation from authoritative formal task, never backfilled from membership.
    class_id = db.Column(db.Integer)
    formal_question_id = db.Column(db.Integer)
    concept_id = db.Column(db.String(80))
    __table_args__ = (db.Index('ix_tutor_session_class_time', 'class_id', 'created_at'),)
    question_ref = db.Column(db.String(100))
    question_version = db.Column(db.String(64))
    lease_token = db.Column(db.String(36))
    lease_until = db.Column(TIMESTAMP)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)


class TutorTurn(db.Model):
    __tablename__ = 'tutor_turns'
    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('tutor_sessions.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    request_hash = db.Column(db.String(64), nullable=False)
    code_hash = db.Column(db.String(64), nullable=False)
    question = db.Column(db.Text, nullable=False)
    mode = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='processing')
    lease_token = db.Column(db.String(36), nullable=False)
    lease_until = db.Column(TIMESTAMP, nullable=False)
    response = db.Column(db.JSON)
    evidence_refs = db.Column(db.JSON, nullable=False, default=list)
    receipt_id = db.Column(db.String(36), db.ForeignKey('tutor_display_receipts.id'))
    error_code = db.Column(db.String(60))
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    completed_at = db.Column(TIMESTAMP)
