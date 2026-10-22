"""Durable tutoring capacity, cancellation and content-free model accounting."""
from . import db
from .learner_state import TIMESTAMP
from app.utils.time import utc_now

class AiRuntimeLock(db.Model):
    __tablename__ = 'ai_runtime_locks'
    scope = db.Column(db.String(32), primary_key=True)
    revision = db.Column(db.Integer, nullable=False, default=0)

class TutorRequestCancellation(db.Model):
    __tablename__ = 'tutor_request_cancellations'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    request_id = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)

class TutorRequestAttempt(db.Model):
    __tablename__ = 'tutor_request_attempts'
    id = db.Column(db.String(36), primary_key=True)
    request_id = db.Column(db.String(36), db.ForeignKey('tutor_turns.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='processing')
    started_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    lease_until = db.Column(TIMESTAMP, nullable=False)
    finished_at = db.Column(TIMESTAMP)
    __table_args__ = (db.Index('ix_tutor_attempt_user_time', 'user_id', 'started_at'), db.Index('ix_tutor_attempt_capacity', 'status', 'lease_until'))

class AiModelCall(db.Model):
    __tablename__ = 'ai_model_calls'
    id = db.Column(db.String(36), primary_key=True)
    workflow = db.Column(db.String(32), nullable=False)
    request_id = db.Column(db.String(36), nullable=False, index=True)
    attempt_id = db.Column(db.String(36), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer)
    prompt_hash = db.Column(db.String(64))
    cached_input_tokens = db.Column(db.Integer)
    cost_status = db.Column(db.String(32), default='in_progress')
    cost_currency = db.Column(db.String(3))
    cost_min = db.Column(db.Numeric(20, 10))
    cost_max = db.Column(db.Numeric(20, 10))
    price_snapshot = db.Column(db.JSON)
    stage = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='processing')
    provider = db.Column(db.String(64))
    model = db.Column(db.String(128))
    policy_version = db.Column(db.String(64), nullable=False)
    state_version = db.Column(db.Integer, nullable=False)
    retrieval_config_hash = db.Column(db.String(64), nullable=False)
    prompt_tokens = db.Column(db.Integer)
    completion_tokens = db.Column(db.Integer)
    total_tokens = db.Column(db.Integer)
    error_code = db.Column(db.String(64))
    elapsed_ms = db.Column(db.Integer)
    started_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    finished_at = db.Column(TIMESTAMP)
    __table_args__ = (db.Index('ix_ai_call_user_time', 'user_id', 'started_at'),db.Index('ix_ai_call_class_time','class_id','started_at'))
