"""用户模型"""
from datetime import datetime
from . import db


class User(db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))

    # 个人信息
    real_name = db.Column(db.String(50))
    avatar_url = db.Column(db.String(255))
    gender = db.Column(db.String(10), default='other')  # male, female, other
    bio = db.Column(db.Text)

    # 角色权限
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, frozen, deleted

    # 激励系统
    level = db.Column(db.Integer, default=1)  # Lv1-Lv5
    total_points = db.Column(db.Integer, default=0)  # 总积分
    consecutive_days = db.Column(db.Integer, default=0)  # 连续学习天数
    last_learn_date = db.Column(db.Date)

    # 班级关联
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)

    # 关系
    role = db.relationship('Role', backref='users')
    class_rel = db.relationship('Class', backref='students', foreign_keys=[class_id])
    achievements = db.relationship('UserAchievement', backref='user', cascade='all, delete-orphan')
    points_logs = db.relationship('PointsLog', backref='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self, include_sensitive=False):
        """转换为字典"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'avatar_url': self.avatar_url,
            'phone': self.phone,
            'gender': self.gender,
            'bio': self.bio,
            'role': self.role.name if self.role else None,
            'status': self.status,
            'level': self.level,
            'total_points': self.total_points,
            'consecutive_days': self.consecutive_days,
            'last_learn_date': self.last_learn_date.isoformat() if self.last_learn_date else None,
            'class_id': self.class_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        return data
