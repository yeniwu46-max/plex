"""Persistent authentication state shared by all application workers."""
from . import db


class AuthSessionState(db.Model):
    __tablename__ = 'auth_session_states'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=0)


class AuthToken(db.Model):
    __tablename__ = 'auth_tokens'
    token_hash = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)


class AuthRateLimit(db.Model):
    __tablename__ = 'auth_rate_limits'
    key_hash = db.Column(db.String(64), primary_key=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)


class OAuthIdentity(db.Model):
    __tablename__ = 'oauth_identities'
    identity_key = db.Column(db.String(160), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
