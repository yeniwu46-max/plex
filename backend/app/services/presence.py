"""Ephemeral student presence tracking for class online counts."""
from __future__ import annotations

from datetime import timedelta

from app.models import User, db
from app.utils.time import utc_now


class PresenceService:
    """Track recent student heartbeats in memory.

    The app uses stateless JWTs, so there is no durable session table to count.
    A short-lived heartbeat gives the UI a real current-online count without
    adding schema churn.
    """

    TTL = timedelta(seconds=90)
    _heartbeats: dict[int, dict] = {}

    @staticmethod
    def _prune(now=None) -> None:
        now = now or utc_now()
        expired = [
            user_id
            for user_id, item in PresenceService._heartbeats.items()
            if now - item['seen_at'] > PresenceService.TTL
        ]
        for user_id in expired:
            PresenceService._heartbeats.pop(user_id, None)

    @staticmethod
    def heartbeat(user_id: int) -> dict:
        now = utc_now()
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        PresenceService._prune(now)
        PresenceService._heartbeats[user_id] = {
            'class_id': user.class_id,
            'seen_at': now,
            'role': user.role.name if user.role else None,
        }
        return PresenceService.class_presence(user_id, now)

    @staticmethod
    def is_online(user_id: int, now=None) -> bool:
        """Whether a student has a non-expired heartbeat."""
        now = now or utc_now()
        PresenceService._prune(now)
        item = PresenceService._heartbeats.get(user_id)
        if not item:
            return False
        return now - item['seen_at'] <= PresenceService.TTL

    @staticmethod
    def online_user_ids(class_id: int | None = None, now=None) -> set[int]:
        now = now or utc_now()
        PresenceService._prune(now)
        ids: set[int] = set()
        for user_id, item in PresenceService._heartbeats.items():
            if item.get('role') != 'student':
                continue
            if class_id is not None and item.get('class_id') != class_id:
                continue
            ids.add(user_id)
        return ids

    @staticmethod
    def class_presence(user_id: int, now=None) -> dict:
        now = now or utc_now()
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        PresenceService._prune(now)
        class_id = user.class_id
        if not class_id:
            online = 1 if user_id in PresenceService._heartbeats else 0
        else:
            online = sum(
                1
                for item in PresenceService._heartbeats.values()
                if item.get('class_id') == class_id and item.get('role') == 'student'
            )
        return {
            'class_id': class_id,
            'online_count': online,
            'ttl_seconds': int(PresenceService.TTL.total_seconds()),
            'updated_at': now.isoformat(),
        }

    @staticmethod
    def class_online_students(class_id: int | None, now=None) -> dict:
        """教师端：返回某班当前心跳在线的学生名单（可刷新）。

        若暂无心跳数据，回退为班级内 status=active 的学生列表，
        并标记 source=class_roster，避免空弹窗无内容可刷。
        """
        now = now or utc_now()
        PresenceService._prune(now)
        if not class_id:
            return {
                'class_id': None,
                'online_count': 0,
                'ttl_seconds': int(PresenceService.TTL.total_seconds()),
                'updated_at': now.isoformat(),
                'source': 'empty',
                'students': [],
            }

        online_ids = [
            user_id
            for user_id, item in PresenceService._heartbeats.items()
            if item.get('class_id') == class_id and item.get('role') == 'student'
        ]
        source = 'heartbeat'
        students = []
        if online_ids:
            rows = User.query.filter(User.id.in_(online_ids)).all()
            by_id = {row.id: row for row in rows}
            for user_id in online_ids:
                user = by_id.get(user_id)
                if not user:
                    continue
                seen = PresenceService._heartbeats.get(user_id, {}).get('seen_at')
                students.append({
                    'id': user.id,
                    'username': user.username,
                    'real_name': user.real_name,
                    'student_no': user.username,
                    'avatar_url': user.avatar_url,
                    'last_seen_at': seen.isoformat() if seen else None,
                })
        else:
            source = 'class_roster'
            rows = (
                User.query.filter_by(class_id=class_id, status='active')
                .order_by(User.id.asc())
                .limit(100)
                .all()
            )
            for user in rows:
                if not user.role or user.role.name != 'student':
                    continue
                students.append({
                    'id': user.id,
                    'username': user.username,
                    'real_name': user.real_name,
                    'student_no': user.username,
                    'avatar_url': user.avatar_url,
                    'last_seen_at': None,
                })
        students.sort(key=lambda item: (item.get('real_name') or item.get('username') or ''))
        return {
            'class_id': class_id,
            'online_count': len(students),
            'ttl_seconds': int(PresenceService.TTL.total_seconds()),
            'updated_at': now.isoformat(),
            'source': source,
            'students': students,
        }
