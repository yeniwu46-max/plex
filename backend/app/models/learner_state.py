"""Durable evidence and versioned projections; no inferred historical backfill."""
from app.models.base import db
from app.utils.time import utc_now
from sqlalchemy.dialects.mysql import DATETIME

TIMESTAMP = db.DateTime().with_variant(DATETIME(fsp=6), "mysql")


class LearningEvent(db.Model):
    __tablename__ = 'learning_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    course = db.Column(db.String(40), nullable=False, default='python')
    dedupe_key = db.Column(db.String(64), nullable=False, unique=True)
    kind = db.Column(db.String(40), nullable=False)
    source_type = db.Column(db.String(40), nullable=False)
    source_id = db.Column(db.String(80), nullable=False)
    source_version = db.Column(db.String(64), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    occurred_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    status = db.Column(db.String(16), nullable=False, default='pending', index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    lease_token = db.Column(db.String(36))
    lease_until = db.Column(TIMESTAMP, index=True)
    retry_at = db.Column(TIMESTAMP)
    error_code = db.Column(db.String(80))
    processed_at = db.Column(TIMESTAMP)


class LearnerState(db.Model):
    __tablename__ = 'learner_states'
    __table_args__ = (db.UniqueConstraint('user_id', 'course', name='uq_learner_state_course'),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course = db.Column(db.String(40), nullable=False, default='python')
    version = db.Column(db.Integer, nullable=False, default=0)
    policy_version = db.Column(db.String(40), nullable=False)
    updated_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)


class LearnerConceptState(db.Model):
    __tablename__ = 'learner_concept_states'
    __table_args__ = (db.UniqueConstraint('state_id', 'concept_id', name='uq_learner_concept'),)
    id = db.Column(db.Integer, primary_key=True)
    state_id = db.Column(db.Integer, db.ForeignKey('learner_states.id'), nullable=False)
    concept_id = db.Column(db.String(80), nullable=False)
    independent_count = db.Column(db.Integer, nullable=False, default=0)
    independent_success = db.Column(db.Integer, nullable=False, default=0)
    assisted_count = db.Column(db.Integer, nullable=False, default=0)
    assisted_success = db.Column(db.Integer, nullable=False, default=0)
    counterexample_count = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    counterexample_success = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    counterexample_last_success_at = db.Column(TIMESTAMP)
    counterexample_review_due_at = db.Column(db.String(40))
    hints_seen = db.Column(db.Integer, nullable=False, default=0)
    review_count = db.Column(db.Integer, nullable=False, default=0)
    review_due_at = db.Column(db.String(40))
    review_updated_at = db.Column(TIMESTAMP)
    last_evidence_at = db.Column(TIMESTAMP)


class LearnerStateChange(db.Model):
    __tablename__ = 'learner_state_changes'
    __table_args__ = (db.UniqueConstraint('state_id', 'version', name='uq_state_change_version'),)
    id = db.Column(db.Integer, primary_key=True)
    state_id = db.Column(db.Integer, db.ForeignKey('learner_states.id'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('learning_events.id'), nullable=False, unique=True)
    base_version = db.Column(db.Integer, nullable=False)
    version = db.Column(db.Integer, nullable=False)
    producer_version = db.Column(db.String(40), nullable=False)
    reason = db.Column(db.String(240), nullable=False)
    changes = db.Column(db.JSON, nullable=False)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)


class TutorDisplayReceipt(db.Model):
    """Only a server-generated, validated response can be acknowledged."""
    __tablename__ = 'tutor_display_receipts'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    course = db.Column(db.String(40), nullable=False, default='python')
    question_id = db.Column(db.Integer, db.ForeignKey('trial_questions.id'))
    concept_id = db.Column(db.String(80))
    mode = db.Column(db.String(32), nullable=False)
    response_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    displayed_at = db.Column(TIMESTAMP)
