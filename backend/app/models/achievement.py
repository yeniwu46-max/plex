"""成就/勋章模型"""
from datetime import datetime
from . import db


class Achievement(db.Model):
    """成就/勋章表"""
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 勋章名
    description = db.Column(db.Text)
    icon_url = db.Column(db.String(255))  # 勋章图标URL
    rarity = db.Column(db.String(20), default='common')  # common, rare, epic, legendary
    condition_type = db.Column(db.String(50))  # 获取条件类型
    condition_value = db.Column(db.Integer)  # 条件数值

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    users = db.relationship('UserAchievement', backref='achievement', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Achievement {self.name}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon_url': self.icon_url,
            'rarity': self.rarity,
            'condition_type': self.condition_type,
            'condition_value': self.condition_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
