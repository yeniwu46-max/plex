"""Dynamic student profile models."""
from . import db
from .base import BaseModel


class StudentProfile(BaseModel):
    __tablename__ = 'student_profiles'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    dimensions = db.Column(db.JSON, nullable=False, default=dict)
    completion_rate = db.Column(db.Integer, nullable=False, default=0)
    version = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship('User', backref=db.backref('dynamic_profile', uselist=False))

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'dimensions': self.dimensions or {},
            'completion_rate': self.completion_rate or 0,
            'version': self.version or 1,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class StudentProfileHistory(BaseModel):
    __tablename__ = 'student_profile_history'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    version = db.Column(db.Integer, nullable=False)
    dimensions = db.Column(db.JSON, nullable=False, default=dict)
    changes = db.Column(db.JSON, nullable=False, default=dict)
    reason = db.Column(db.String(64), nullable=False, default='conversation')
    backend = db.Column(db.String(32), nullable=False, default='local_rules')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'version': self.version,
            'dimensions': self.dimensions or {},
            'changes': self.changes or {},
            'reason': self.reason,
            'backend': self.backend,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class StudentProfileSuggestion(BaseModel):
    __tablename__ = 'student_profile_suggestions'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    dimension = db.Column(db.String(64), nullable=False, index=True)
    proposed_value = db.Column(db.String(500), nullable=False)
    evidence = db.Column(db.JSON, nullable=False, default=list)
    source = db.Column(db.String(32), nullable=False, default='behavior')
    status = db.Column(db.String(16), nullable=False, default='pending', index=True)
    profile_version = db.Column(db.Integer, nullable=False, default=0)
    resolved_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'dimension': self.dimension,
            'proposed_value': self.proposed_value,
            'evidence': self.evidence or [],
            'source': self.source,
            'status': self.status,
            'profile_version': self.profile_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


class StudentProfileDiagnostic(BaseModel):
    """Optional onboarding assessment, kept separate from conversational profile evidence."""
    __tablename__ = 'student_profile_diagnostics'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    status = db.Column(db.String(16), nullable=False, default='pending')  # pending | completed | skipped
    answers = db.Column(db.JSON, nullable=False, default=dict)
    mastery = db.Column(db.JSON, nullable=False, default=dict)
    completed_at = db.Column(db.DateTime)
    skipped_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'status': self.status,
            'answers': self.answers or {},
            'mastery': self.mastery or {},
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'skipped_at': self.skipped_at.isoformat() if self.skipped_at else None,
        }


class LearningAdaptation(BaseModel):
    """Auditable deterministic intervention for one student and knowledge point."""
    __tablename__ = 'learning_adaptations'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    knowledge_key = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default='active', index=True)  # active | recovered
    trigger_evidence = db.Column(db.JSON, nullable=False, default=dict)
    action_plan = db.Column(db.JSON, nullable=False, default=dict)
    profile_version = db.Column(db.Integer, nullable=False, default=0)
    remedial_completed = db.Column(db.Integer, nullable=False, default=0)
    remedial_correct = db.Column(db.Integer, nullable=False, default=0)
    resolved_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id, 'knowledge_key': self.knowledge_key, 'status': self.status,
            'trigger_evidence': self.trigger_evidence or {}, 'action_plan': self.action_plan or {},
            'profile_version': self.profile_version, 'remedial_completed': self.remedial_completed,
            'remedial_correct': self.remedial_correct,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }
