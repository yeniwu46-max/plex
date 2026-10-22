"""Read-only keyset history, pinned to one learner state version and current access."""
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import db, User, Class
from app.models.learner_state import LearnerState, LearnerStateChange, LearningEvent
from app.services.tutor_context import TutorContextError

CURSOR_AGE = 3600
MAX_VERSION = 2147483647


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='plex.learning-evidence.v1')


def public_change(change, event):
    """An allowlist, shared with the compact state snapshot. No payload/changes dump."""
    payload = event.payload if isinstance(event.payload, dict) else {}
    text = lambda key, limit: payload[key][:limit] if isinstance(payload.get(key), str) else None
    qid = payload.get('question_id')
    return {'event_id': event.id, 'version': change.version, 'kind': event.kind, 'reason': change.reason,
        'policy_version': change.producer_version,
        'concept_id': text('concept_id', 80), 'question_title': text('question_title', 120),
        'question_id': qid if type(qid) is int and qid > 0 else None,
        'evidence_scope': text('evidence_scope', 64),
        'occurred_at': event.occurred_at.isoformat(), 'processed_at': change.created_at.isoformat()}


def page(actor_id, student_id, *, cursor=None, limit=20, snapshot_version=None):
    if type(limit) is not int or not 1 <= limit <= 50:
        raise TutorContextError('每页条数须为 1–50 的整数')
    if snapshot_version is not None and (type(snapshot_version) is not int or not 0 <= snapshot_version <= MAX_VERSION):
        raise TutorContextError('学习状态版本无效')
    if cursor is not None and snapshot_version is not None:
        raise TutorContextError('继续翻页时请只使用原翻页凭据，不要另行指定版本')
    decoded = None
    if cursor is not None:
        if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048:
            raise TutorContextError('翻页凭据无效，请刷新学习证据')
        try:
            decoded = _serializer().loads(cursor, max_age=CURSOR_AGE)
        except SignatureExpired:
            raise TutorContextError('翻页凭据已过期，请刷新学习证据', 410) from None
        except BadSignature:
            raise TutorContextError('翻页凭据无效，请刷新学习证据') from None
        if (not isinstance(decoded, dict) or type(decoded.get('format')) is not int or decoded['format'] != 1
            or set(decoded) != {'format','actor','student','audience','state','version','before'}
            or any(type(decoded[k]) is not int or not 0 < decoded[k] <= MAX_VERSION
                   for k in ('actor','student','state','version','before'))
            or decoded['before'] > decoded['version'] or decoded.get('audience') not in ('student','teacher')):
            raise TutorContextError('翻页凭据格式无效，请刷新学习证据')
    with Session(db.engine) as session:
        if session.get_bind().dialect.name == 'sqlite':
            session.connection().exec_driver_sql('BEGIN')
        elif session.get_bind().dialect.name == 'mysql':
            session.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        actor = session.get(User, actor_id)
        student = session.get(User, student_id)
        audience = actor.role.name if actor and actor.role else None
        if (not actor or actor.status != 'active' or not student or not student.role
            or student.role.name != 'student' or student.status not in ('active','frozen')):
            raise TutorContextError('无权查看该学生的学习证据', 403)
        if audience == 'student':
            allowed = actor_id == student_id
        elif audience == 'teacher':
            classroom = session.get(Class, student.class_id) if student.class_id else None
            allowed = bool(classroom and classroom.teacher_id == actor_id)
        else:
            allowed = False
        if not allowed or (decoded and (decoded['actor'] != actor_id or decoded['student'] != student_id
                                        or decoded['audience'] != audience)):
            raise TutorContextError('无权查看该学生的学习证据', 403)
        state = session.scalar(select(LearnerState).where(LearnerState.user_id == student_id,
                                                         LearnerState.course == 'python'))
        latest = state.version if state else 0
        version = decoded['version'] if decoded else latest if snapshot_version is None else snapshot_version
        if version > latest or (decoded and (not state or state.id != decoded['state'])):
            raise TutorContextError('学习状态已变化，请刷新学习证据后重新查看', 409)
        before = decoded['before'] if decoded else version + 1
        rows = session.execute(select(LearnerStateChange, LearningEvent).join(
            LearningEvent, LearningEvent.id == LearnerStateChange.event_id).where(
            LearnerStateChange.state_id == state.id if state else False,
            LearnerStateChange.version <= version, LearnerStateChange.version < before,
            LearningEvent.user_id == student_id, LearningEvent.course == 'python',
        ).order_by(LearnerStateChange.version.desc()).limit(limit + 1)).all()
        has_more = len(rows) > limit
        items = [public_change(change, event) for change, event in rows[:limit]]
        next_cursor = _serializer().dumps({'format':1, 'actor':actor_id, 'student':student_id,
            'audience':audience, 'state':state.id, 'version':version, 'before':items[-1]['version']}) if has_more else None
        return {'course':'python', 'snapshot_version':version, 'latest_version':latest,
                'items':items, 'has_more':has_more, 'next_cursor':next_cursor, 'limit':limit}
