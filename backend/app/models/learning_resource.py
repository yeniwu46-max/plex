"""学习资源目录"""
from . import db


class LearningResource(db.Model):
    __tablename__ = 'learning_resources'

    id = db.Column(db.Integer, primary_key=True)
    knowledge_key = db.Column(db.String(32), nullable=False, index=True)
    resource_type = db.Column(db.String(24), nullable=False, default='article')
    title = db.Column(db.String(200), nullable=False)
    content_ref = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, default=50)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'knowledge_key': self.knowledge_key,
            'type': self.resource_type,
            'title': self.title,
            'content_ref': self.content_ref,
            'difficulty': self.difficulty,
            'is_active': self.is_active,
        }
