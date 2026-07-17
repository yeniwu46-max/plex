"""学生入班申请（教师审核）。"""
from app.utils.time import utc_now

from . import db


class ClassEnrollmentRequest(db.Model):
    __tablename__ = 'class_enrollment_requests'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    message = db.Column(db.Text)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utc_now)
    reviewed_at = db.Column(db.DateTime)

    student = db.relationship('User', foreign_keys=[student_id], backref='class_enrollment_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    class_rel = db.relationship('Class', foreign_keys=[class_id])

    def to_dict(self):
        student = self.student
        class_obj = self.class_rel
        reviewer = self.reviewer
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': student.real_name or student.username if student else None,
            'student_username': student.username if student else None,
            'class_id': self.class_id,
            'class_name': class_obj.name if class_obj else None,
            'join_code': class_obj.join_code if class_obj else None,
            'teacher_name': class_obj.teacher.real_name if class_obj and class_obj.teacher else None,
            'status': self.status,
            'message': self.message,
            'reviewer_id': self.reviewer_id,
            'reviewer_name': reviewer.real_name or reviewer.username if reviewer else None,
            'review_note': self.review_note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
