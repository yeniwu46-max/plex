"""学生对战真实匹配队列（基于 Presence 同班在线心跳）。"""
from __future__ import annotations

import random
import uuid
from datetime import timedelta

from app.models import User, db
from app.services.presence import PresenceService
from app.utils.time import utc_now

# 与前端 classArenaQuestions 题池 id 对齐
ENTRY_QUESTION_POOL = [
    'arena-gladiator-sum',
    'arena-gladiator-max',
    'arena-gladiator-product',
]
ADVANCED_QUESTION_POOL = [
    'class-hard-sum-two',
    'class-hard-max-two',
    'class-hard-positive-sum',
]

DIFFICULTY_META = {
    'entry': {'label': '入门', 'time_sec': 300, 'pool': ENTRY_QUESTION_POOL, 'count': 3},
    'advanced': {'label': '进阶', 'time_sec': 600, 'pool': ADVANCED_QUESTION_POOL, 'count': 3},
}


class DuelMatchService:
    """内存匹配队列：同班 + 同难度的等待者配对，共享同一套题。"""

    QUEUE_TTL = timedelta(minutes=3)
    MATCH_TTL = timedelta(minutes=30)
    _queue: dict[str, list[dict]] = {}
    _matches: dict[str, dict] = {}
    _user_match: dict[int, str] = {}

    @staticmethod
    def _prune(now=None) -> None:
        now = now or utc_now()
        for key, waiters in list(DuelMatchService._queue.items()):
            alive = [item for item in waiters if now - item['joined_at'] <= DuelMatchService.QUEUE_TTL]
            if alive:
                DuelMatchService._queue[key] = alive
            else:
                DuelMatchService._queue.pop(key, None)
        expired = [
            match_id
            for match_id, match in DuelMatchService._matches.items()
            if now - match['created_at'] > DuelMatchService.MATCH_TTL
        ]
        for match_id in expired:
            match = DuelMatchService._matches.pop(match_id, None)
            if not match:
                continue
            for uid in (match.get('player_a'), match.get('player_b')):
                if uid and DuelMatchService._user_match.get(uid) == match_id:
                    DuelMatchService._user_match.pop(uid, None)

    @staticmethod
    def _queue_key(class_id: int, difficulty: str) -> str:
        return f'{class_id}:{difficulty}'

    @staticmethod
    def _user_brief(user_id: int) -> dict:
        user = db.session.get(User, user_id)
        if not user:
            return {'user_id': user_id, 'display_name': f'学员{user_id}'}
        name = (user.real_name or user.username or '').strip() or f'学员{user_id}'
        return {
            'user_id': user.id,
            'display_name': name,
            'username': user.username,
            'real_name': user.real_name,
        }

    @staticmethod
    def _pick_questions(difficulty: str) -> list[str]:
        meta = DIFFICULTY_META[difficulty]
        pool = list(meta['pool'])
        random.shuffle(pool)
        return pool[: meta['count']]

    @staticmethod
    def _serialize_match(match: dict, viewer_id: int) -> dict:
        opponent_id = match['player_b'] if match['player_a'] == viewer_id else match['player_a']
        difficulty = match['difficulty']
        meta = DIFFICULTY_META[difficulty]
        return {
            'status': 'matched',
            'match_id': match['match_id'],
            'difficulty': difficulty,
            'difficulty_label': meta['label'],
            'time_sec': meta['time_sec'],
            'question_ids': list(match['question_ids']),
            'opponent': DuelMatchService._user_brief(opponent_id),
            'created_at': match['created_at'].isoformat(),
        }

    @staticmethod
    def online_classmates(user_id: int) -> dict:
        """学生端：同班当前心跳在线同学（不含自己）。"""
        PresenceService.heartbeat(user_id)
        now = utc_now()
        DuelMatchService._prune(now)
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')
        class_id = user.class_id
        if not class_id:
            return {
                'class_id': None,
                'online_count': 0,
                'ttl_seconds': int(PresenceService.TTL.total_seconds()),
                'updated_at': now.isoformat(),
                'students': [],
            }
        online_ids = [
            uid
            for uid in PresenceService.online_user_ids(class_id, now)
            if uid != user_id
        ]
        students = []
        if online_ids:
            rows = User.query.filter(User.id.in_(online_ids)).all()
            by_id = {row.id: row for row in rows}
            for uid in online_ids:
                row = by_id.get(uid)
                if not row:
                    continue
                students.append({
                    'id': row.id,
                    'username': row.username,
                    'real_name': row.real_name,
                    'avatar_url': row.avatar_url,
                    'last_seen_at': (
                        PresenceService._heartbeats.get(uid, {}).get('seen_at').isoformat()
                        if PresenceService._heartbeats.get(uid, {}).get('seen_at')
                        else None
                    ),
                })
        students.sort(key=lambda item: (item.get('real_name') or item.get('username') or ''))
        return {
            'class_id': class_id,
            'online_count': len(students),
            'ttl_seconds': int(PresenceService.TTL.total_seconds()),
            'updated_at': now.isoformat(),
            'students': students,
        }

    @staticmethod
    def join(
        user_id: int,
        difficulty: str = 'entry',
        opponent_id: int | None = None,
    ) -> dict:
        PresenceService.heartbeat(user_id)
        now = utc_now()
        DuelMatchService._prune(now)

        difficulty = (difficulty or 'entry').strip().lower()
        if difficulty not in DIFFICULTY_META:
            raise ValueError('difficulty 必须为 entry 或 advanced')

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')
        if not user.class_id:
            raise ValueError('请先加入班级后再匹配对战')

        existing_id = DuelMatchService._user_match.get(user_id)
        if existing_id and existing_id in DuelMatchService._matches:
            return DuelMatchService._serialize_match(DuelMatchService._matches[existing_id], user_id)

        online_ids = PresenceService.online_user_ids(user.class_id, now)
        rivals = [uid for uid in online_ids if uid != user_id]
        if not rivals:
            raise ValueError('当前同班没有其他在线同学，请等待同学上线后再匹配')

        # 指定邀请：对方必须在线
        if opponent_id is not None:
            opponent_id = int(opponent_id)
            if opponent_id == user_id:
                raise ValueError('不能与自己对战')
            if opponent_id not in online_ids:
                raise ValueError('该同学当前不在线，无法邀请')
            return DuelMatchService._create_match(
                user.class_id, difficulty, user_id, opponent_id, now
            )

        key = DuelMatchService._queue_key(user.class_id, difficulty)
        waiters = DuelMatchService._queue.setdefault(key, [])
        # 已在队列中则返回等待态
        for item in waiters:
            if item['user_id'] == user_id:
                return {
                    'status': 'waiting',
                    'difficulty': difficulty,
                    'difficulty_label': DIFFICULTY_META[difficulty]['label'],
                    'time_sec': DIFFICULTY_META[difficulty]['time_sec'],
                    'online_rivals': len(rivals),
                    'message': '正在等待其他在线同学加入匹配队列…',
                }

        # 找同难度等待中且仍在线的对手
        partner = None
        remaining = []
        for item in waiters:
            if item['user_id'] in online_ids and item['user_id'] != user_id and partner is None:
                partner = item
            elif item['user_id'] != user_id:
                remaining.append(item)
        DuelMatchService._queue[key] = remaining

        if partner:
            return DuelMatchService._create_match(
                user.class_id, difficulty, user_id, partner['user_id'], now
            )

        waiters = DuelMatchService._queue.setdefault(key, [])
        waiters.append({'user_id': user_id, 'joined_at': now})
        return {
            'status': 'waiting',
            'difficulty': difficulty,
            'difficulty_label': DIFFICULTY_META[difficulty]['label'],
            'time_sec': DIFFICULTY_META[difficulty]['time_sec'],
            'online_rivals': len(rivals),
            'message': f'同班有 {len(rivals)} 名在线同学，已进入匹配队列，等待对方点击「寻找对手」…',
        }

    @staticmethod
    def _create_match(
        class_id: int,
        difficulty: str,
        player_a: int,
        player_b: int,
        now=None,
    ) -> dict:
        now = now or utc_now()
        match_id = uuid.uuid4().hex[:16]
        match = {
            'match_id': match_id,
            'class_id': class_id,
            'difficulty': difficulty,
            'player_a': player_a,
            'player_b': player_b,
            'question_ids': DuelMatchService._pick_questions(difficulty),
            'created_at': now,
        }
        DuelMatchService._matches[match_id] = match
        DuelMatchService._user_match[player_a] = match_id
        DuelMatchService._user_match[player_b] = match_id
        # 清掉双方可能残留的排队
        key = DuelMatchService._queue_key(class_id, difficulty)
        DuelMatchService._queue[key] = [
            item for item in DuelMatchService._queue.get(key, [])
            if item['user_id'] not in (player_a, player_b)
        ]
        return DuelMatchService._serialize_match(match, player_a)

    @staticmethod
    def status(user_id: int) -> dict:
        PresenceService.heartbeat(user_id)
        now = utc_now()
        DuelMatchService._prune(now)
        match_id = DuelMatchService._user_match.get(user_id)
        if match_id and match_id in DuelMatchService._matches:
            return DuelMatchService._serialize_match(DuelMatchService._matches[match_id], user_id)

        user = db.session.get(User, user_id)
        if not user or not user.class_id:
            return {'status': 'idle', 'message': '未在匹配中'}

        for difficulty in DIFFICULTY_META:
            key = DuelMatchService._queue_key(user.class_id, difficulty)
            for item in DuelMatchService._queue.get(key, []):
                if item['user_id'] == user_id:
                    rivals = [
                        uid for uid in PresenceService.online_user_ids(user.class_id, now)
                        if uid != user_id
                    ]
                    return {
                        'status': 'waiting',
                        'difficulty': difficulty,
                        'difficulty_label': DIFFICULTY_META[difficulty]['label'],
                        'time_sec': DIFFICULTY_META[difficulty]['time_sec'],
                        'online_rivals': len(rivals),
                        'message': '正在等待其他在线同学加入匹配队列…',
                    }
        return {'status': 'idle', 'message': '未在匹配中'}

    @staticmethod
    def cancel(user_id: int) -> dict:
        now = utc_now()
        DuelMatchService._prune(now)
        match_id = DuelMatchService._user_match.pop(user_id, None)
        if match_id:
            match = DuelMatchService._matches.pop(match_id, None)
            if match:
                other = match['player_b'] if match['player_a'] == user_id else match['player_a']
                if DuelMatchService._user_match.get(other) == match_id:
                    DuelMatchService._user_match.pop(other, None)
        user = db.session.get(User, user_id)
        if user and user.class_id:
            for difficulty in DIFFICULTY_META:
                key = DuelMatchService._queue_key(user.class_id, difficulty)
                DuelMatchService._queue[key] = [
                    item for item in DuelMatchService._queue.get(key, [])
                    if item['user_id'] != user_id
                ]
        return {'status': 'idle', 'message': '已取消匹配'}
