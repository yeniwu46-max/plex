"""教师班级变更审批申请。"""
import json
from datetime import datetime

from . import db


class ClassChangeRequest(db.Model):
    __tablename__ = 'class_change_requests'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # create, update, delete
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    payload_json = db.Column(db.Text, nullable=False, default='{}')
    reason = db.Column(db.Text)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    requester = db.relationship('User', foreign_keys=[requester_id], backref='class_change_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    class_rel = db.relationship('Class', foreign_keys=[class_id])

    @property
    def payload(self) -> dict:
        try:
            return json.loads(self.payload_json or '{}')
        except json.JSONDecodeError:
            return {}

    @payload.setter
    def payload(self, value: dict):
        self.payload_json = json.dumps(value or {}, ensure_ascii=False)

    def to_dict(self):
        requester = self.requester
        class_obj = self.class_rel
        return {
            'id': self.id,
            'requester_id': self.requester_id,
            'requester_name': requester.real_name or requester.username if requester else None,
            'action': self.action,
            'status': self.status,
            'class_id': self.class_id,
            'class_name': class_obj.name if class_obj else self.payload.get('name'),
            'payload': self.payload,
            'reason': self.reason,
            'reviewer_id': self.reviewer_id,
            'review_note': self.review_note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
