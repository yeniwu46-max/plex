"""Personalized resource generation models."""
from . import db
from .base import BaseModel


class ResourceGenerationTask(BaseModel):
    __tablename__ = 'resource_generation_tasks'

    task_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    knowledge_key = db.Column(db.String(32), nullable=False, index=True)
    requested_types = db.Column(db.JSON, nullable=False, default=list)
    status = db.Column(db.String(16), nullable=False, default='pending', index=True)
    progress = db.Column(db.Integer, nullable=False, default=0)
    current_agent = db.Column(db.String(64))
    steps = db.Column(db.JSON, nullable=False, default=list)
    backend = db.Column(db.String(32), nullable=False, default='local_rules')
    fallback_reason = db.Column(db.String(255))
    error = db.Column(db.String(500))
    retry_of = db.Column(db.String(64))
    profile_version = db.Column(db.Integer, nullable=False, default=0)
    request_fingerprint = db.Column(db.String(64), nullable=False, default='', index=True)
    idempotency_key = db.Column(db.String(100), index=True)
    recoverable = db.Column(db.Boolean, nullable=False, default=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    audit_report = db.Column(db.JSON)

    def to_dict(self, resources=None):
        return {
            'task_id': self.task_id,
            'status': self.status,
            'progress': self.progress,
            'current_agent': self.current_agent,
            'steps': self.steps or [],
            'resources': resources or [],
            'error': self.error,
            'backend': self.backend,
            'fallback_reason': self.fallback_reason,
            'retry_of': self.retry_of,
            'profile_version': self.profile_version or 0,
            'request_fingerprint': self.request_fingerprint,
            'recoverable': bool(self.recoverable),
            'audit_report': self.audit_report,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class PersonalizedLearningResource(BaseModel):
    __tablename__ = 'personalized_learning_resources'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    generation_task_id = db.Column(
        db.String(64),
        db.ForeignKey('resource_generation_tasks.task_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    knowledge_key = db.Column(db.String(32), nullable=False, index=True)
    knowledge_label = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(32), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.JSON, nullable=False, default=dict)
    content_url = db.Column(db.String(500))
    difficulty = db.Column(db.Integer, nullable=False, default=50)
    estimated_minutes = db.Column(db.Integer, nullable=False, default=15)
    profile_snapshot = db.Column(db.JSON, nullable=False, default=dict)
    recommendation_reason = db.Column(db.Text, nullable=False)
    citations = db.Column(db.JSON, nullable=False, default=list)
    confidence = db.Column(db.Float, nullable=False, default=0.8)
    review_status = db.Column(db.String(24), nullable=False, default='approved', index=True)
    review_reason = db.Column(db.String(500))
    risk_reasons = db.Column(db.JSON, nullable=False, default=list)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    generator_agent = db.Column(db.String(64), nullable=False, default='resource_generator')
    backend = db.Column(db.String(32), nullable=False, default='local_rules')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'knowledge_key': self.knowledge_key,
            'knowledge_label': self.knowledge_label,
            'resource_type': self.resource_type,
            'title': self.title,
            'content': self.content or {},
            'content_url': self.content_url,
            'difficulty': self.difficulty,
            'estimated_minutes': self.estimated_minutes,
            'profile_snapshot': self.profile_snapshot or {},
            'recommendation_reason': self.recommendation_reason,
            'citations': self.citations or [],
            'confidence': self.confidence,
            'review_status': self.review_status,
            'review_reason': self.review_reason,
            'risk_reasons': self.risk_reasons or [],
            'generator_agent': self.generator_agent,
            'generation_task_id': self.generation_task_id,
            'backend': self.backend,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
