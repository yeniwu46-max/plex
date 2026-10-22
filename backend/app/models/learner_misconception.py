"""Evidence-linked, reviewable misconception candidates; never model facts."""
from app.models.base import db
from app.models.learner_state import TIMESTAMP
from app.utils.time import utc_now


class LearnerMisconception(db.Model):
    __tablename__ = 'learner_misconceptions'
    __table_args__ = (db.UniqueConstraint('state_id', 'concept_id', 'kind', name='uq_state_misconception'),)
    id = db.Column(db.Integer, primary_key=True)
    state_id = db.Column(db.Integer, db.ForeignKey('learner_states.id'), nullable=False, index=True)
    concept_id = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='candidate')
    revision = db.Column(db.Integer, nullable=False, default=1)
    updated_version = db.Column(db.Integer, nullable=False)
    manual_status = db.Column(db.String(16))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_note = db.Column(db.String(300))
    reviewed_at = db.Column(TIMESTAMP)
    last_signal_at = db.Column(TIMESTAMP, nullable=False)
    updated_at = db.Column(TIMESTAMP, nullable=False, default=utc_now)


class LearnerMisconceptionEvidence(db.Model):
    __tablename__ = 'learner_misconception_evidence'
    __table_args__ = (db.UniqueConstraint('misconception_id', 'event_id', name='uq_misconception_event'),)
    id = db.Column(db.Integer, primary_key=True)
    misconception_id = db.Column(db.Integer, db.ForeignKey('learner_misconceptions.id'), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('learning_events.id'), nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    observation = db.Column(db.String(240), nullable=False)
