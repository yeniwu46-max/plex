# -*- coding: utf-8 -*-
"""将指定学生账号配置为满级测试号：解锁星轨路径、全知识点 AC、满级封顶 XP。"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_ROOT))

from app import create_app
from app.constants.test_accounts import (
    DOMAIN_PROGRESS_KEYS,
    MAX_LEVEL_TOTAL_POINTS,
    SLOTS_PER_KNOWLEDGE_POINT,
    STAR_PATH_KNOWLEDGE_POINT_IDS,
    TEST_SANDBOX_USERNAMES,
)
from app.data.knowledge_node_registry import KNOWLEDGE_NODE_REGISTRY
from app.models import (
    Achievement,
    StudentMistake,
    Trial,
    TrialParticipation,
    TrialQuestion,
    TrialQuestionProgress,
    User,
    UserAchievement,
    db,
)
from app.services.incentive import IncentiveService, MAX_LEVEL
from app.services.mistake import MistakeService
from app.services.student_progress import DOMAIN_CATALOG
from app.utils.time import utc_now


def _gen_question_ids() -> list[str]:
    ids: list[str] = []
    for kp_id in STAR_PATH_KNOWLEDGE_POINT_IDS:
        for slot in range(SLOTS_PER_KNOWLEDGE_POINT):
            ids.append(f'gen-{kp_id}-s{slot}')
    return ids


def _knowledge_key_for_kp(kp_id: str) -> str:
    for entry in KNOWLEDGE_NODE_REGISTRY:
        if entry.star_path_id == kp_id and entry.knowledge_keys:
            return entry.knowledge_keys[0]
    fallback = {
        'stage4-bubble': 'algo-sort',
        'stage4-selection': 'algo-sort',
        'stage4-binary': 'algo-search',
    }
    return fallback.get(kp_id, 'algo')


def _ensure_domain_trials(user: User) -> int:
    """为七大学域写入已完成试炼，使 get_learning_path 进度为 100% 且域间解锁。"""
    if not user.class_id:
        raise ValueError(f'用户 {user.username} 未加入班级，无法写入试炼完成记录')

    teacher_id = (
        db.session.query(Trial.teacher_id)
        .filter(Trial.class_id == user.class_id)
        .order_by(Trial.id.asc())
        .limit(1)
        .scalar()
    )
    if not teacher_id:
        teacher = User.query.filter_by(username='teacher001').first()
        teacher_id = teacher.id if teacher else user.id

    created = 0
    now = utc_now()
    for domain_key, knowledge_key in DOMAIN_PROGRESS_KEYS:
        trial = (
            Trial.query.filter_by(class_id=user.class_id, knowledge_key=knowledge_key)
            .order_by(Trial.id.asc())
            .first()
        )
        if not trial:
            domain_title = next((d['title'] for d in DOMAIN_CATALOG if d['key'] == domain_key), domain_key)
            trial = Trial(
                class_id=user.class_id,
                teacher_id=teacher_id,
                title=f'{domain_title} 通关试炼',
                trial_type='solo',
                knowledge_key=knowledge_key,
                difficulty=100,
                duration_minutes=60,
                status='ended',
                reward_points=0,
            )
            db.session.add(trial)
            db.session.flush()
            created += 1

        participation = TrialParticipation.query.filter_by(trial_id=trial.id, user_id=user.id).first()
        if not participation:
            participation = TrialParticipation(trial_id=trial.id, user_id=user.id)
            db.session.add(participation)
        participation.status = 'completed'
        participation.score = 100
        participation.completed_at = now
    return created


def _seed_accepted_questions(user_id: int) -> int:
    count = 0
    for kp_id in STAR_PATH_KNOWLEDGE_POINT_IDS:
        knowledge_key = _knowledge_key_for_kp(kp_id)
        for slot in range(SLOTS_PER_KNOWLEDGE_POINT):
            ref = f'gen-{kp_id}-s{slot}'
            MistakeService._upsert(
                user_id,
                source='code_trial',
                knowledge_key=knowledge_key,
                question_ref=ref,
                question_title=f'通关试炼 · {kp_id} 第{slot + 1}题',
                meta={'bootstrap': True, 'knowledge_point': kp_id},
                passed=True,
            )
            count += 1
    return count


def _normalize_completed_trials(user_id: int) -> int:
    parts = TrialParticipation.query.filter_by(user_id=user_id, status='completed').all()
    for part in parts:
        part.score = 100
    return len(parts)


def _resolve_active_mistakes(user_id: int) -> int:
    now = utc_now()
    rows = StudentMistake.query.filter_by(user_id=user_id).all()
    for row in rows:
        row.last_passed_at = now
        row.fail_count = 0
    return len(rows)


def _seed_knowledge_graph_progress(user_id: int) -> int:
    """每知识节点至少 2 次正确答题，使图谱状态为 mastered。"""
    touched = 0
    keys_seen: set[str] = set()
    for entry in KNOWLEDGE_NODE_REGISTRY:
        key = entry.knowledge_keys[0] if entry.knowledge_keys else entry.kg_id
        if key in keys_seen:
            continue
        keys_seen.add(key)
        questions = (
            TrialQuestion.query.filter_by(question_type='coding', knowledge_key=key)
            .order_by(TrialQuestion.id.asc())
            .limit(3)
            .all()
        )
        if not questions:
            continue
        for question in questions[:2]:
            row = TrialQuestionProgress.query.filter_by(
                user_id=user_id,
                question_id=question.id,
            ).first()
            if not row:
                row = TrialQuestionProgress(user_id=user_id, question_id=question.id)
                db.session.add(row)
            row.status = 'completed'
            row.is_correct = True
            touched += 1
    return touched


def _unlock_all_achievements(user_id: int) -> int:
    unlocked = {
        row.achievement_id for row in UserAchievement.query.filter_by(user_id=user_id).all()
    }
    added = 0
    for achievement in Achievement.query.all():
        if achievement.id in unlocked:
            continue
        db.session.add(UserAchievement(user_id=user_id, achievement_id=achievement.id))
        added += 1
    return added


def _needs_bootstrap(user: User) -> bool:
    if user.username not in TEST_SANDBOX_USERNAMES:
        return False
    sample_ref = f'gen-{STAR_PATH_KNOWLEDGE_POINT_IDS[0]}-s0'
    existing = StudentMistake.query.filter_by(
        user_id=user.id,
        question_ref=sample_ref,
        source='code_trial',
    ).first()
    return existing is None or existing.last_passed_at is None


def _bootstrap_user(user: User) -> dict:
    user.level = MAX_LEVEL
    user.total_points = MAX_LEVEL_TOTAL_POINTS
    user.consecutive_days = max(user.consecutive_days or 0, 30)
    user.bio = (user.bio or '').strip() or '测试账号 · 学习路径已全部解锁'

    trials = _ensure_domain_trials(user)
    normalized = _normalize_completed_trials(user.id)
    resolved_mistakes = _resolve_active_mistakes(user.id)
    ac_count = _seed_accepted_questions(user.id)
    graph_rows = _seed_knowledge_graph_progress(user.id)
    achievements = _unlock_all_achievements(user.id)

    IncentiveService.sync_user_level(user)
    db.session.commit()

    return {
        'username': user.username,
        'level': user.level,
        'total_points': user.total_points,
        'max_level': MAX_LEVEL,
        'xp_capped': user.username in TEST_SANDBOX_USERNAMES,
        'domain_trials_touched': trials,
        'completed_trials_normalized': normalized,
        'mistakes_resolved': resolved_mistakes,
        'accepted_questions': ac_count,
        'graph_progress_rows': graph_rows,
        'achievements_unlocked': achievements,
        'gen_question_ids': len(_gen_question_ids()),
    }


def ensure_test_sandbox_accounts() -> None:
    """开发环境启动时为测试学生账号补齐全解锁进度（幂等）。"""
    for username in TEST_SANDBOX_USERNAMES:
        user = User.query.filter_by(username=username).first()
        if not user or not _needs_bootstrap(user):
            continue
        _bootstrap_user(user)


def bootstrap_test_student(username: str = 'student001') -> dict:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            raise ValueError(f'未找到用户 {username}')
        return _bootstrap_user(user)


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'student001'
    report = bootstrap_test_student(target)
    print(report)
