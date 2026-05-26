"""每日委托服务"""
from datetime import date, datetime, time

from .base import BaseService
from app.models import DailyQuest, PointsLog, User, UserDailyQuest, db


DAILY_BONUS_XP = 120
DAILY_BONUS_REASON = 'daily_quest_bonus'

DEFAULT_DAILY_QUESTS = [
    {
        'key': 'morning-launch',
        'period': '晨间',
        'time': '08:00',
        'title': '晨间启动',
        'description': '查看今日推荐路线，开启探索之旅',
        'total': 1,
        'reward_xp': 20,
        'sort_order': 10,
    },
    {
        'key': 'fragment-repair',
        'period': '上午',
        'time': '10:00',
        'title': '修复知识碎片',
        'description': '修复 2 个知识碎片，填补认知缺口',
        'total': 2,
        'reward_xp': 40,
        'sort_order': 20,
    },
    {
        'key': 'trial-challenge',
        'period': '下午',
        'time': '14:00',
        'title': '试炼挑战',
        'description': '完成 1 次试炼关卡挑战',
        'total': 1,
        'reward_xp': 35,
        'sort_order': 30,
    },
    {
        'key': 'night-summary',
        'period': '夜晚',
        'time': '21:00',
        'title': '夜间总结',
        'description': '生成今日成长报告，记录进步',
        'total': 1,
        'reward_xp': 25,
        'sort_order': 40,
    },
]


class DailyQuestService(BaseService):
    """每日委托业务逻辑"""

    @staticmethod
    def ensure_default_quests():
        for item in DEFAULT_DAILY_QUESTS:
            quest = DailyQuest.query.filter_by(key=item['key']).first()
            if quest:
                continue
            db.session.add(DailyQuest(**item))
        db.session.commit()

    @staticmethod
    def get_today(user_id):
        today = date.today()
        records = DailyQuestService._ensure_today_records(user_id, today)
        return DailyQuestService._build_today_payload(user_id, today, records)

    @staticmethod
    def advance_progress(user_id, quest_key):
        today = date.today()
        records = DailyQuestService._ensure_today_records(user_id, today)
        record = next((item for item in records if item.quest and item.quest.key == quest_key), None)
        if not record:
            raise Exception('今日委托不存在或未启用')

        quest = record.quest
        if record.current < quest.total:
            record.current += 1
            if record.current >= quest.total and not record.completed_at:
                record.completed_at = datetime.utcnow()
                if not record.reward_claimed_at:
                    DailyQuestService._add_points(
                        user_id=user_id,
                        points=quest.reward_xp,
                        reason=f'daily_quest:{quest.key}',
                        related_id=quest.id,
                    )
                    record.reward_claimed_at = datetime.utcnow()
            db.session.commit()

        refreshed = DailyQuestService._ensure_today_records(user_id, today)
        return DailyQuestService._build_today_payload(user_id, today, refreshed)

    @staticmethod
    def claim_bonus(user_id):
        today = date.today()
        records = DailyQuestService._ensure_today_records(user_id, today)
        payload = DailyQuestService._build_today_payload(user_id, today, records)
        if not payload['all_completed']:
            raise Exception('今日委托尚未全部完成')
        if not payload['bonus_claimed']:
            DailyQuestService._add_points(
                user_id=user_id,
                points=DAILY_BONUS_XP,
                reason=DAILY_BONUS_REASON,
            )
            db.session.commit()
        refreshed = DailyQuestService._ensure_today_records(user_id, today)
        return DailyQuestService._build_today_payload(user_id, today, refreshed)

    @staticmethod
    def _ensure_today_records(user_id, target_date):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')

        quests = DailyQuest.query.filter_by(is_active=True).order_by(DailyQuest.sort_order.asc(), DailyQuest.id.asc()).all()
        existing = UserDailyQuest.query.filter_by(user_id=user_id, quest_date=target_date).all()
        existing_by_quest_id = {item.quest_id: item for item in existing}
        created = False

        for quest in quests:
            if quest.id in existing_by_quest_id:
                continue
            record = UserDailyQuest(user_id=user_id, quest_id=quest.id, quest_date=target_date)
            db.session.add(record)
            existing.append(record)
            created = True

        db.session.flush()
        if created:
            db.session.commit()
        existing_by_quest_id = {item.quest_id: item for item in existing}
        return [existing_by_quest_id[quest.id] for quest in quests if quest.id in existing_by_quest_id]

    @staticmethod
    def _build_today_payload(user_id, target_date, records):
        total_required = sum(item.quest.total for item in records if item.quest)
        total_current = sum(min(item.current, item.quest.total) for item in records if item.quest)
        completed_count = sum(1 for item in records if item.completed_at)
        earned_xp = sum(item.quest.reward_xp for item in records if item.quest and item.reward_claimed_at)
        bonus_claimed = DailyQuestService._bonus_claimed(user_id, target_date)

        return {
            'date': target_date.isoformat(),
            'quests': [item.to_dict() for item in records],
            'completed_count': completed_count,
            'total_count': len(records),
            'total_required': total_required,
            'total_current': total_current,
            'earned_xp': earned_xp,
            'bonus_xp': DAILY_BONUS_XP,
            'bonus_claimed': bonus_claimed,
            'all_completed': bool(records) and completed_count == len(records),
        }

    @staticmethod
    def _add_points(user_id, points, reason, related_id=None):
        user = User.query.get(user_id)
        if not user:
            raise Exception('用户不存在')
        db.session.add(PointsLog(user_id=user_id, points=points, reason=reason, related_id=related_id))
        user.total_points = (user.total_points or 0) + points

    @staticmethod
    def _bonus_claimed(user_id, target_date):
        start = datetime.combine(target_date, time.min)
        end = datetime.combine(target_date, time.max)
        return PointsLog.query.filter(
            PointsLog.user_id == user_id,
            PointsLog.reason == DAILY_BONUS_REASON,
            PointsLog.created_at >= start,
            PointsLog.created_at <= end,
        ).first() is not None
