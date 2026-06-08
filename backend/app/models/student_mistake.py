"""学生错题本（选择题、编程试炼、紧急任务）"""
import json

from . import db


class StudentMistake(db.Model):
    __tablename__ = 'student_mistakes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    source = db.Column(db.String(20), nullable=False, default='mcq')  # mcq | code_trial | emergency
    knowledge_key = db.Column(db.String(32), nullable=False, default='algo', index=True)
    question_ref = db.Column(db.String(64), nullable=False, index=True)
    question_title = db.Column(db.String(256))
    error_type = db.Column(db.String(32))  # wrong_answer | wrong_output | runtime_error
    fail_count = db.Column(db.Integer, nullable=False, default=1)
    last_failed_at = db.Column(db.DateTime, nullable=False)
    last_passed_at = db.Column(db.DateTime)
    meta = db.Column(db.JSON)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'source', 'question_ref', name='uq_user_mistake_ref'),
    )

    user = db.relationship('User', backref=db.backref('mistakes', lazy='dynamic'))

    def to_dict(self):
        meta = self.meta if isinstance(self.meta, dict) else {}
        if isinstance(self.meta, str):
            try:
                meta = json.loads(self.meta or '{}')
            except json.JSONDecodeError:
                meta = {}
        return {
            'id': self.id,
            'user_id': self.user_id,
            'source': self.source,
            'knowledge_key': self.knowledge_key,
            'knowledge_label': meta.get('knowledge_label'),
            'question_ref': self.question_ref,
            'question_id': self.question_ref,
            'question_title': self.question_title or meta.get('question_title') or '',
            'topic': meta.get('topic') or '',
            'tags': meta.get('tags') or [],
            'star_path_node_id': meta.get('star_path_node_id'),
            'star_path_node_title': meta.get('star_path_node_title'),
            'failed_case_labels': meta.get('failed_case_labels') or [],
            'error_types': meta.get('error_types') or ([self.error_type] if self.error_type else []),
            'error_type': self.error_type,
            'fail_count': self.fail_count,
            'last_failed_at': self.last_failed_at.isoformat() if self.last_failed_at else None,
            'last_passed_at': self.last_passed_at.isoformat() if self.last_passed_at else None,
            'meta': meta,
        }
