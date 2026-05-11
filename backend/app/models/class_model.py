"""班级模型"""
from datetime import datetime
from . import db


class Class(db.Model):
    """班级表"""
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    grade_level = db.Column(db.Integer)  # 年级
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    student_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    teacher = db.relationship('User', backref='teaching_classes', foreign_keys=[teacher_id])

    def __repr__(self):
        return f'<Class {self.name}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'grade_level': self.grade_level,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.real_name if self.teacher else None,
            'student_count': self.student_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
