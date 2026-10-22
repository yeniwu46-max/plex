"""Bounded, content-free classroom observations, not causal learning estimates."""
from collections import Counter
from datetime import timedelta
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import db, User, Role, Class
from app.models.ai_runtime import AiModelCall, TutorRequestAttempt
from app.models.learner_state import LearningEvent, TutorDisplayReceipt
from app.models.tutor_session import TutorSession, TutorTurn
from app.services.tutor_context import TutorContextError
from app.utils.time import utc_now

POLICY = 'classroom-observation-v1'
ROW_LIMIT = 10000
FOLLOWUP_DAYS = 7


def _bounded(session, statement, limit=ROW_LIMIT):
    rows = session.execute(statement.limit(limit + 1)).all()
    if len(rows) > limit:
        raise TutorContextError('观察数据量较大，请缩短统计时间范围', 422)
    return rows


def _latency(values, total):
    valid = sorted(v for v in values if type(v) is int and v >= 0)
    return {'samples': len(valid), 'missing': total - len(valid),
            'p50': valid[ceil(len(valid) * .5) - 1] if valid else None,
            'p95': valid[ceil(len(valid) * .95) - 1] if valid else None}


def _duration(start, end):
    return int((end - start).total_seconds() * 1000) if start and end and end >= start else None


def snapshot(actor_id, class_id, days=14):
    if type(days) is not int or days not in (7, 14, 30):
        raise TutorContextError('统计范围仅支持最近 7、14 或 30 天')
    now = utc_now()
    start = now - timedelta(days=days)
    with Session(db.engine) as session:
        actor = session.get(User, actor_id)
        classroom = session.get(Class, class_id)
        if (not actor or actor.status != 'active' or not actor.role or actor.role.name != 'teacher'
                or not classroom or classroom.teacher_id != actor.id):
            raise TutorContextError('无权查看该班级的试用观察', 403)
        members = select(User.id).join(Role, Role.id == User.role_id).where(
            User.class_id == class_id, User.status == 'active', Role.name == 'student')
        member_count = session.scalar(select(func.count()).select_from(members.subquery()))
        cohort = select(TutorTurn.id).join(TutorSession, TutorSession.id == TutorTurn.session_id).where(
            TutorSession.class_id == class_id, TutorSession.formal_question_id.is_not(None),
            TutorTurn.user_id == TutorSession.user_id, TutorTurn.user_id.in_(members),
            TutorTurn.created_at >= start, TutorTurn.created_at < now)
        # No question, code, generated response, email, token or provider endpoint is loaded.
        rows = _bounded(session, select(TutorTurn.id, TutorTurn.user_id, TutorTurn.status,
            TutorTurn.created_at, TutorTurn.completed_at, TutorTurn.lease_until,
            TutorSession.concept_id, TutorSession.formal_question_id,
            TutorDisplayReceipt.id.label('receipt_id'), TutorDisplayReceipt.user_id.label('receipt_user'),
            TutorDisplayReceipt.question_id.label('receipt_question'), TutorDisplayReceipt.mode,
            TutorDisplayReceipt.displayed_at).join(TutorSession, TutorSession.id == TutorTurn.session_id)
            .outerjoin(TutorDisplayReceipt, TutorDisplayReceipt.id == TutorTurn.receipt_id)
            .where(TutorTurn.id.in_(cohort)).order_by(TutorTurn.created_at, TutorTurn.id))
        attempts = _bounded(session, select(TutorRequestAttempt.status, TutorRequestAttempt.started_at,
            TutorRequestAttempt.finished_at, TutorRequestAttempt.lease_until)
            .join(TutorTurn, TutorTurn.id == TutorRequestAttempt.request_id).where(
            TutorRequestAttempt.request_id.in_(cohort), TutorRequestAttempt.user_id == TutorTurn.user_id,
            TutorRequestAttempt.started_at < now), ROW_LIMIT * 3)
        calls = _bounded(session, select(AiModelCall.status, AiModelCall.elapsed_ms,
            AiModelCall.finished_at).join(TutorTurn, TutorTurn.id == AiModelCall.request_id)
            .where(AiModelCall.workflow == 'tutor',
            AiModelCall.request_id.in_(cohort), AiModelCall.user_id == TutorTurn.user_id,
            AiModelCall.started_at < now), ROW_LIMIT * 10)
        events = _bounded(session, select(LearningEvent.user_id, LearningEvent.payload, LearningEvent.occurred_at,
            LearningEvent.id).where(LearningEvent.user_id.in_(members), LearningEvent.course == 'python',
            LearningEvent.kind == 'submission_graded', LearningEvent.source_type == 'trial_question_progress',
            LearningEvent.source_version == '1', LearningEvent.occurred_at >= start,
            LearningEvent.occurred_at < now).order_by(LearningEvent.occurred_at, LearningEvent.id))

    states = Counter()
    displayed, published, completed = set(), set(), []
    anchors = {}  # One exposure per student/concept; repeated hints cannot multiply outcomes.
    for r in rows:
        state = r.status
        if state == 'processing' and r.lease_until <= now:
            state = 'expired'
        if state == 'complete' and (not r.completed_at or r.completed_at >= now):
            state = 'processing'
        states[state] += 1
        if state != 'complete':
            continue
        completed.append(r)
        if (not r.receipt_id or r.receipt_user != r.user_id or r.receipt_question != r.formal_question_id
                or r.mode == 'conversation'):
            continue
        published.add(r.receipt_id)
        if not r.displayed_at or not r.completed_at <= r.displayed_at < now:
            continue
        displayed.add(r.receipt_id)
        if r.concept_id and r.concept_id != 'unclassified':
            key = (r.user_id, r.concept_id)
            anchor = (r.displayed_at, r.formal_question_id)
            if key not in anchors or anchor < anchors[key]:
                anchors[key] = anchor

    formal = Counter(total=0, independent=0, independent_correct=0, assisted=0, assisted_correct=0)
    matches = {}
    for event in events:
        p = event.payload or {}
        if (type(p.get('class_id')) is not int or p['class_id'] != class_id
                or p.get('evidence_scope') != 'server_graded'
                or type(p.get('correct')) is not bool or type(p.get('assisted')) is not bool
                or type(p.get('question_id')) is not int or p['question_id'] <= 0):
            continue
        formal['total'] += 1
        bucket = 'assisted' if p['assisted'] else 'independent'
        formal[bucket] += 1
        formal[bucket + '_correct'] += int(p['correct'])
        concept = p.get('concept_id')
        if not isinstance(concept, str):
            continue
        key = (event.user_id, concept)
        anchor = anchors.get(key)
        if (anchor and key not in matches and not p['assisted'] and p['question_id'] != anchor[1]
                and anchor[0] < event.occurred_at <= anchor[0] + timedelta(days=FOLLOWUP_DAYS)):
            matches[key] = p['correct']  # First eligible result; never cherry-pick a later success.
    open_windows = sum(key not in matches and now < anchor[0] + timedelta(days=FOLLOWUP_DAYS)
                       for key, anchor in anchors.items())
    finished_calls = [c for c in calls if c.finished_at and c.finished_at < now and c.status != 'processing']
    finished_attempts = [a for a in attempts if a.finished_at and a.finished_at < now and a.status != 'processing']
    return {'policy_version': POLICY, 'scope': 'current_students_frozen_formal_class', 'class_id': class_id,
        'window': {'days': days, 'start': start.isoformat() + 'Z', 'as_of': now.isoformat() + 'Z'},
        'current_students': member_count, 'tutoring_students': len({r.user_id for r in rows}),
        'flow': {'requests': len(rows), 'states': dict(states), 'published_help': len(published),
                 'display_confirmed': len(displayed), 'not_display_confirmed': len(published - displayed)},
        'formal_practice': dict(formal),
        'followup': {'unit': 'student_concept_first_display', 'days': FOLLOWUP_DAYS, 'exposures': len(anchors),
            'observed': len(matches), 'first_correct': sum(matches.values()),
            'first_incorrect': len(matches) - sum(matches.values()), 'window_open': open_windows,
            'window_closed_without_observation': len(anchors) - len(matches) - open_windows},
        'latency_ms': {'method': 'nearest_rank',
            'completed_request': _latency([_duration(r.created_at, r.completed_at) for r in completed], len(completed)),
            'finished_attempt': _latency([_duration(a.started_at, a.finished_at) for a in finished_attempts], len(finished_attempts)),
            'finished_model_call': _latency([c.elapsed_ms for c in finished_calls], len(finished_calls)),
            'model_by_status': {s: _latency([c.elapsed_ms for c in finished_calls if c.status == s],
                                sum(c.status == s for c in finished_calls)) for s in sorted({c.status for c in finished_calls})},
            'attempts': len(attempts), 'unfinished_attempts': len(attempts) - len(finished_attempts),
            'model_calls': len(calls), 'unfinished_model_calls': len(calls) - len(finished_calls)},
        'limitations': ['仅统计当前有效学生及发生时已绑定本班的正式题目辅导和判题；旧记录、自由聊天和自测不回填。',
            '展示回执证明页面报告已展示，不证明学生阅读或理解；生成完成也不等于教学审核通过或有效帮助。',
            '后续观察按学生与知识点去重，从本窗口首次展示起七天内，取另一题的首次平台内未展示提示的正式判题；不证明没有课外帮助或学习因果提升。',
            '请求时长从首次接纳到完成，包含重试等待；尝试时长和物理模型调用时长分别统计，不是首字或页面端到端延迟。',
            '没有观察到后续练习不算失败；滚动窗口与当前班级成员变动会改变本次统计。']}
