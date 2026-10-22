"""Teacher-owned immutable specifications/versions and append-only gate reports."""
from .base import db
from .learner_state import TIMESTAMP
from app.utils.time import utc_now


class CounterexampleSpec(db.Model):
    __tablename__ = 'counterexample_specs'
    id = db.Column(db.String(36), primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, index=True)
    content = db.Column(db.JSON, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    approved_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)


class CounterexampleChallenge(db.Model):
    __tablename__ = 'counterexample_challenges'
    id = db.Column(db.String(36), primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, index=True)
    current_revision = db.Column(db.Integer, nullable=False, default=1)
    published_revision = db.Column(db.Integer)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)


class CounterexampleVersion(db.Model):
    __tablename__ = 'counterexample_versions'
    id = db.Column(db.String(36), primary_key=True)
    challenge_id = db.Column(db.String(36), db.ForeignKey('counterexample_challenges.id'), nullable=False, index=True)
    revision = db.Column(db.Integer, nullable=False)
    spec_id = db.Column(db.String(36), db.ForeignKey('counterexample_specs.id'), nullable=False)
    candidate = db.Column(db.JSON, nullable=False)
    manifest_hash = db.Column(db.String(64), nullable=False)
    origin = db.Column(db.String(30), nullable=False)
    source_template = db.Column(db.JSON)
    blocked_reason = db.Column(db.String(80))
    latest_report_id = db.Column(db.String(36))
    reviewed_report_id = db.Column(db.String(36))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_note = db.Column(db.Text)
    reviewed_at = db.Column(TIMESTAMP)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    __table_args__ = (db.UniqueConstraint('challenge_id', 'revision', name='uq_counterexample_revision'),)


class CounterexampleValidation(db.Model):
    __tablename__ = 'counterexample_validations'
    id = db.Column(db.String(36), primary_key=True)
    version_id = db.Column(db.String(36), db.ForeignKey('counterexample_versions.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    manifest_hash = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    lease_token = db.Column(db.String(36), nullable=False)
    lease_until = db.Column(TIMESTAMP, nullable=False)
    report = db.Column(db.JSON)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    completed_at = db.Column(TIMESTAMP)


class CounterexampleAttempt(db.Model):
    __tablename__ = 'counterexample_attempts'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    version_id = db.Column(db.String(36), db.ForeignKey('counterexample_versions.id'), nullable=False, index=True)
    validation_id = db.Column(db.String(36), db.ForeignKey('counterexample_validations.id'), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    input_value = db.Column(db.JSON, nullable=False)
    expected_output = db.Column(db.JSON, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    lease_token = db.Column(db.String(36), nullable=False)
    lease_until = db.Column(TIMESTAMP, nullable=False)
    result = db.Column(db.JSON)
    execution_report = db.Column(db.JSON)
    explanation_review = db.Column(db.JSON)
    review_revision = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    completed_at = db.Column(TIMESTAMP)


class CounterexampleExplanationReview(db.Model):
    __tablename__ = 'counterexample_explanation_reviews'
    id = db.Column(db.String(36), primary_key=True)
    attempt_id = db.Column(db.String(36), db.ForeignKey('counterexample_attempts.id'), nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    revision = db.Column(db.Integer, nullable=False)
    verdict = db.Column(db.String(24), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    __table_args__ = (db.UniqueConstraint('attempt_id', 'revision', name='uq_counterexample_explanation_revision'),)


class CounterexampleGenerationTask(db.Model):
    __tablename__ = 'counterexample_generation_tasks'
    id = db.Column(db.String(36), primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    spec_id = db.Column(db.String(36), db.ForeignKey('counterexample_specs.id'), nullable=False)
    spec_hash = db.Column(db.String(64), nullable=False)
    bug_kind = db.Column(db.String(30), nullable=False)
    # Reserved IDs make recovery idempotent even after a process dies mid-stage.
    challenge_id = db.Column(db.String(36), nullable=False, unique=True)
    version_id = db.Column(db.String(36), db.ForeignKey('counterexample_versions.id'), unique=True)
    validation_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='queued')
    stage = db.Column(db.String(20), nullable=False, default='generation')
    attempts = db.Column(db.Integer, nullable=False, default=0)
    lease_token = db.Column(db.String(36))
    lease_until = db.Column(TIMESTAMP)
    error_code = db.Column(db.String(60))
    generation_audit = db.Column(db.JSON)
    pedagogy_review = db.Column(db.JSON)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    completed_at = db.Column(TIMESTAMP)
    __table_args__ = (
        db.Index('ix_counterexample_generation_owner', 'teacher_id', 'created_at'),
        db.Index('ix_counterexample_generation_queue', 'status', 'lease_until'),
    )


class CounterexampleGenerationCall(db.Model):
    __tablename__ = 'counterexample_generation_calls'
    id = db.Column(db.String(36), primary_key=True)
    task_id = db.Column(db.String(36), db.ForeignKey('counterexample_generation_tasks.id'), nullable=False, index=True)
    attempt = db.Column(db.Integer, nullable=False)
    stage = db.Column(db.String(20), nullable=False)
    audit = db.Column(db.JSON)
    created_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)
    completed_at = db.Column(TIMESTAMP)
