"""试炼题目评论区。"""
from app.utils.time import utc_now

from . import db


class TrialComment(db.Model):
    __tablename__ = 'trial_comments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question_ref = db.Column(db.String(64), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('trial_comments.id', ondelete='CASCADE'), nullable=True, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = db.relationship('User', backref=db.backref('trial_comments', lazy='dynamic'))
    parent = db.relationship('TrialComment', remote_side=[id], backref=db.backref('replies', lazy='dynamic'))
    likes = db.relationship('TrialCommentLike', backref='comment', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, *, like_count: int = 0, liked_by_me: bool = False, replies: list | None = None):
        author = self.user
        return {
            'id': self.id,
            'user_id': self.user_id,
            'author_name': (author.real_name or author.username) if author else '匿名',
            'author_avatar_url': author.avatar_url if author else None,
            'question_ref': self.question_ref,
            'parent_id': self.parent_id,
            'content': self.content,
            'like_count': like_count,
            'liked_by_me': liked_by_me,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'replies': replies or [],
        }


class TrialCommentLike(db.Model):
    __tablename__ = 'trial_comment_likes'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('trial_comments.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    user = db.relationship('User', backref=db.backref('trial_comment_likes', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('comment_id', 'user_id', name='uq_trial_comment_like'),
    )
