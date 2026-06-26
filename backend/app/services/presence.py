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
