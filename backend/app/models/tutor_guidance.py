"""Durable coaching requests; display confirmation is not evidence of mastery."""
from app.utils.time import utc_now
from .base import db


class TutorGuidanceTurn(db.Model):
    __tablename__ = 'tutor_guidance_turns'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_id = db.Column(db.String(36), nullable=False)
    input_hash = db.Column(db.String(64), nullable=False)
    scope_hash = db.Column(db.String(64), nullable=False)
    focus = db.Column(db.String(40), nullable=False)
    mode = db.Column(db.String(24), nullable=False)
    stage = db.Column(db.Integer, nullable=False)
    result = db.Column(db.JSON)
    lease_token = db.Column(db.String(36))
    lease_expires_at = db.Column(db.DateTime)
    displayed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'request_id', name='uq_tutor_guidance_request'),
    )
