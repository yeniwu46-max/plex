"""Durable identities and bounded attempts for teacher/admin course answers."""
from . import db
from .learner_state import TIMESTAMP
from app.utils.time import utc_now


class RagRequest(db.Model):
    __tablename__ = 'rag_requests'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    body_hash = db.Column(db.String(64), nullable=False)
    policy_version = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='processing')
    lease_token = db.Column(db.String(36), nullable=False)
    lease_until = db.Column(TIMESTAMP, nullable=False)
    response = db.Column(db.JSON)
    evidence_refs = db.Column(db.JSON)
    error_code = db.Column(db.String(64))
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    completed_at = db.Column(TIMESTAMP)


class RagRequestAttempt(db.Model):
    __tablename__ = 'rag_request_attempts'
    id = db.Column(db.String(36), primary_key=True)
    request_id = db.Column(db.String(36), db.ForeignKey('rag_requests.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='processing')
    started_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    lease_until = db.Column(TIMESTAMP, nullable=False)
    finished_at = db.Column(TIMESTAMP)
    __table_args__ = (db.Index('ix_rag_attempt_user_time', 'user_id', 'started_at'),
                      db.Index('ix_rag_attempt_capacity', 'status', 'lease_until'))
