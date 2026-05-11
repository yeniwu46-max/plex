"""成就服务"""
from .base import BaseService
from app.models import Achievement, UserAchievement, User, db
from datetime import datetime


class AchievementService(BaseService):
    """成就服务"""

    @staticmethod
    def create_achievement(name, description, icon_url, rarity, condition_type, condition_value):
        """创建成就"""
        achievement = Achievement(
            name=name,
            description=description,
            icon_url=icon_url,
            rarity=rarity,
            condition_type=condition_type,
            condition_value=condition_value
        )
        
        db.session.add(achievement)
        db.session.commit()
        
        return achievement

    @staticmethod
    def get_achievements(rarity=None):
        """获取成就列表"""
        query = Achievement.query
        
        if rarity:
            query = query.filter_by(rarity=rarity)
        
        achievements = query.all()
        return [a.to_dict() for a in achievements]

    @staticmethod
    def unlock_achievement(user_id, achievement_id):
        """解锁成就"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        achievement = Achievement.query.get(achievement_id)
        if not achievement:
            raise Exception('成就不存在')
        
        # 检查是否已解锁
        existing = UserAchievement.query.filter_by(
            user_id=user_id,
            achievement_id=achievement_id
        ).first()
        
        if existing:
            raise Exception('该成就已解锁')
        
        ua = UserAchievement(user_id=user_id, achievement_id=achievement_id)
        db.session.add(ua)
        db.session.commit()

    @staticmethod
    def get_user_achievements(user_id):
        """获取用户成就"""
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        achievements = [a.to_dict() for a in user.achievements]
        
        return {
            'user_id': user_id,
            'achievements': achievements,
            'count': len(achievements)
        }

    @staticmethod
    def add_points(user_id, points, reason, related_id=None):
        """添加积分"""
        from app.models import PointsLog
        
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        
        # 添加积分日志
        log = PointsLog(
            user_id=user_id,
            points=points,
            reason=reason,
            related_id=related_id
        )
        db.session.add(log)
        
        # 更新用户总积分
        user.total_points += points
        
        db.session.commit()
        
        return user

    @staticmethod
    def get_points_log(user_id, page=1, limit=20):
        """获取积分日志"""
        from app.models import PointsLog
        
        query = PointsLog.query.filter_by(user_id=user_id)
        total = query.count()
        
        logs = query.order_by(PointsLog.created_at.desc()).offset(
            (page - 1) * limit
        ).limit(limit).all()
        
        return {
            'total': total,
            'page': page,
            'limit': limit,
            'logs': [log.to_dict() for log in logs]
        }
