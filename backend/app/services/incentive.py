"""积分、等级、成就、排名闭环"""
from datetime import date, datetime, timedelta

from sqlalchemy import func

from app.models import (
    Achievement,
    PointsLog,
    RankingCache,
    TrialParticipation,
    User,
    UserAchievement,
    UserDailyQuest,
    db,
)

from .base import BaseService

# 累计 XP 阈值：Lv1..Lv5
LEVEL_THRESHOLDS = [0, 500, 1500, 3000, 5000, 10_000]
MAX_LEVEL = 5
LEVEL_TITLES = {
    1: '见习 Explorer',
    2: '星轨行者',
    3: '深空探索者',
    4: '星域领航员',
    5: '传奇 Explorer',
}


class IncentiveService(BaseService):
    @staticmethod
    def current_week_key(moment=None):
        moment = moment or datetime.utcnow()
        return f'{moment.year}-w{moment.isocalendar()[1]:02d}'

    @staticmethod
    def level_from_points(points):
        value = points or 0
        level = 1
        for idx in range(1, len(LEVEL_THRESHOLDS)):
            if value >= LEVEL_THRESHOLDS[idx]:
                level = min(idx + 1, MAX_LEVEL)
            else:
                break
        return level

    @staticmethod
    def level_profile(user):
        points = user.total_points or 0
        level = user.level or 1
        current_floor = LEVEL_THRESHOLDS[level - 1]
        next_ceiling = LEVEL_THRESHOLDS[level] if level < MAX_LEVEL else None
        if next_ceiling:
            span = next_ceiling - current_floor
            progress = round(((points - current_floor) / span) * 100) if span else 100
            points_to_next = max(0, next_ceiling - points)
        else:
            progress = 100
            points_to_next = 0
        return {
            'level': level,
            'title': LEVEL_TITLES.get(level, f'Lv{level}'),
            'total_points': points,
            'current_threshold': current_floor,
            'next_threshold': next_ceiling,
            'points_to_next_level': points_to_next,
            'progress_percent': min(100, max(0, progress)),
            'max_level': MAX_LEVEL,
        }

    @staticmethod
    def _metric_value(user_id, condition_type):
        user = User.query.get(user_id)
        if not user:
            return 0
        if condition_type == 'total_points':
            return user.total_points or 0
        if condition_type == 'level':
            return user.level or 1
        if condition_type == 'consecutive_days':
            return user.consecutive_days or 0
        if condition_type == 'trials_completed':
            return (
                TrialParticipation.query.filter_by(user_id=user_id, status='completed').count()
            )
        if condition_type == 'daily_quests_completed':
            return UserDailyQuest.query.filter(
                UserDailyQuest.user_id == user_id,
                UserDailyQuest.completed_at.isnot(None),
            ).count()
        if condition_type == 'complete_course':
            return UserDailyQuest.query.filter(
                UserDailyQuest.user_id == user_id,
                UserDailyQuest.completed_at.isnot(None),
            ).count()
        return 0

    @staticmethod
    def check_and_unlock_achievements(user_id):
        unlocked_ids = {
            row.achievement_id
            for row in UserAchievement.query.filter_by(user_id=user_id).all()
        }
        newly = []
        for achievement in Achievement.query.all():
            if achievement.id in unlocked_ids:
                continue
            if not achievement.condition_type:
                continue
            current = IncentiveService._metric_value(user_id, achievement.condition_type)
            target = achievement.condition_value or 0
            if current >= target:
                db.session.add(UserAchievement(user_id=user_id, achievement_id=achievement.id))
                newly.append(achievement.to_dict())
        return newly

    @staticmethod
    def sync_user_level(user):
        previous = user.level or 1
        new_level = IncentiveService.level_from_points(user.total_points)
        user.level = new_level
        return previous, new_level

    @staticmethod
    def class_rank_for_user(user):
        if not user.class_id:
            return None
        week = IncentiveService.current_week_key()
        cached = RankingCache.query.filter_by(
            class_id=user.class_id, user_id=user.id, week=week
        ).first()
        if cached:
            return cached.rank
        rank_count = (
            db.session.query(func.count(User.id))
            .filter(User.class_id == user.class_id, User.total_points > (user.total_points or 0))
            .scalar()
        )
        return (rank_count or 0) + 1

    @staticmethod
    def week_points(user_id, week_key=None):
        week_key = week_key or IncentiveService.current_week_key()
        year_str, week_str = week_key.split('-w')
        year = int(year_str)
        week = int(week_str)
        start = datetime.fromisocalendar(year, week, 1)
        end = start + timedelta(days=7)
        total = (
            db.session.query(func.coalesce(func.sum(PointsLog.points), 0))
            .filter(
                PointsLog.user_id == user_id,
                PointsLog.created_at >= start,
                PointsLog.created_at < end,
            )
            .scalar()
        )
        return int(total or 0)

    @staticmethod
    def refresh_class_ranking(class_id, week_key=None):
        week_key = week_key or IncentiveService.current_week_key()
        students = User.query.filter_by(class_id=class_id, status='active').all()
        if not students:
            return []

        scored = []
        for student in students:
            IncentiveService.sync_user_level(student)
            scored.append(
                {
                    'student': student,
                    'week_points': IncentiveService.week_points(student.id, week_key),
                    'total_points': student.total_points or 0,
                }
            )
        scored.sort(key=lambda row: (row['week_points'], row['total_points']), reverse=True)

        RankingCache.query.filter_by(class_id=class_id, week=week_key).delete()
        rows = []
        for idx, row in enumerate(scored, start=1):
            student = row['student']
            cache = RankingCache(
                class_id=class_id,
                user_id=student.id,
                rank=idx,
                points=row['week_points'],
                level=student.level or 1,
                week=week_key,
            )
            db.session.add(cache)
            rows.append(cache)
        db.session.flush()
        return rows

    @staticmethod
    def process_user_incentive(user_id, refresh_ranking=True):
        user = User.query.get(user_id)
        if not user:
            raise ValueError('用户不存在')

        previous_level = user.level or 1
        previous_points = user.total_points or 0
        IncentiveService.sync_user_level(user)
        newly_unlocked = IncentiveService.check_and_unlock_achievements(user_id)
        class_rank = None
        if refresh_ranking and user.class_id:
            IncentiveService.refresh_class_ranking(user.class_id)
            class_rank = IncentiveService.class_rank_for_user(user)
        elif user.class_id:
            class_rank = IncentiveService.class_rank_for_user(user)

        db.session.flush()
        return IncentiveService.build_feedback(
            user,
            previous_level=previous_level,
            previous_points=previous_points,
            newly_unlocked=newly_unlocked,
            class_rank=class_rank,
        )

    @staticmethod
    def build_feedback(user, previous_level, previous_points, newly_unlocked, class_rank):
        profile = IncentiveService.level_profile(user)
        return {
            'total_points': user.total_points or 0,
            'level': user.level or 1,
            'title': profile['title'],
            'level_up': (user.level or 1) > (previous_level or 1),
            'previous_level': previous_level,
            'level_profile': profile,
            'unlocked_achievements': newly_unlocked,
            'class_rank': class_rank,
            'points_gained': (user.total_points or 0) - (previous_points or 0),
        }

    @staticmethod
    def record_points(user_id, points, reason, related_id=None, refresh_ranking=True):
        if not points:
            return IncentiveService.process_user_incentive(user_id, refresh_ranking=refresh_ranking)

        user = User.query.get(user_id)
        if not user:
            raise ValueError('用户不存在')

        previous_level = user.level or 1
        previous_points = user.total_points or 0

        db.session.add(
            PointsLog(
                user_id=user_id,
                points=points,
                reason=reason,
                related_id=related_id,
            )
        )
        user.total_points = (user.total_points or 0) + points

        feedback = IncentiveService.process_user_incentive(user_id, refresh_ranking=refresh_ranking)
        feedback['points_gained'] = points
        feedback['previous_level'] = previous_level
        feedback['level_up'] = (user.level or 1) > previous_level
        return feedback

    @staticmethod
    def incentive_summary(user_id):
        user = User.query.get(user_id)
        if not user:
            raise ValueError('用户不存在')
        profile = IncentiveService.level_profile(user)
        unlocked = UserAchievement.query.filter_by(user_id=user_id).count()
        total_achievements = Achievement.query.count()
        next_achievements = []
        unlocked_ids = {
            row.achievement_id for row in UserAchievement.query.filter_by(user_id=user_id).all()
        }
        for achievement in Achievement.query.order_by(Achievement.id.asc()).all():
            if achievement.id in unlocked_ids:
                continue
            current = IncentiveService._metric_value(user_id, achievement.condition_type)
            target = achievement.condition_value or 0
            if target <= 0:
                continue
            next_achievements.append(
                {
                    **achievement.to_dict(),
                    'current_value': current,
                    'target_value': target,
                    'progress_percent': min(100, round((current / target) * 100)),
                }
            )
            if len(next_achievements) >= 3:
                break

        return {
            'level_profile': profile,
            'class_rank': IncentiveService.class_rank_for_user(user),
            'achievements_unlocked': unlocked,
            'achievements_total': total_achievements,
            'next_achievements': next_achievements,
            'week_key': IncentiveService.current_week_key(),
            'week_points': IncentiveService.week_points(user_id),
        }
