"""排名缓存模型"""
from datetime import datetime
from . import db


class RankingCache(db.Model):
    """排名缓存表"""
    __tablename__ = 'ranking_cache'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rank = db.Column(db.Integer)
    points = db.Column(db.Integer)
    level = db.Column(db.Integer)
    week = db.Column(db.String(10))  # 2024-w20

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('class_id', 'user_id', 'week', name='unique_ranking'),
        db.ForeignKeyConstraint(['class_id'], ['classes.id']),
        db.ForeignKeyConstraint(['user_id'], ['users.id']),
    )

    def __repr__(self):
        return f'<RankingCache class_id={self.class_id} rank={self.rank}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'class_id': self.class_id,
            'user_id': self.user_id,
            'rank': self.rank,
            'points': self.points,
            'level': self.level,
            'week': self.week,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
