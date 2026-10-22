"""Short admission transactions, recoverable answers and fresh source authorization.

Admission limits logical attempts, not physical provider calls after a crashed lease.
The model ledger separately counts actual HTTP attempts. No prompts in this ledger.
"""
import hashlib
import uuid
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta

from flask import current_app
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import db, User, KnowledgeChunk
from app.models.rag_runtime import RagRequest as Request, RagRequestAttempt as Attempt
from app.services.ai_admission import admission_lock
from app.services.knowledge.access_service import KnowledgeAccessService as Access
from app.services.knowledge.rag_service import KnowledgeRagService
from app.services.knowledge.schemas import RagAnswer
from app.services.knowledge.settings import retrieval_config
from app.services.learner_state import fingerprint
from app.services.model_accounting import scope, update_scope
from app.services.tutor_context import TutorContextError
from app.utils.time import utc_now

POLICY = 'rag-admission-v1'
LEASE_SECONDS = 300


class RagRuntimeError(TutorContextError):
    def __init__(self, message, status=409, reason='request_conflict'):
        super().__init__(message, status)
        self.reason = reason


def request_uuid(value):
    try:
        if not isinstance(value, str) or len(value) != 36:
            raise ValueError()
        return str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise RagRuntimeError('请求编号必须为 UUID', 400, 'invalid_request') from None


def limits():
    return {name: max(1, int(current_app.config.get(key, default))) for name, key, default in (
        ('request_limit', 'RAG_DAILY_REQUEST_LIMIT', 40),
        ('concurrency_limit', 'RAG_USER_CONCURRENCY', 2),
        ('global_concurrency', 'RAG_GLOBAL_CONCURRENCY', 8),
        ('attempt_limit', 'RAG_REQUEST_ATTEMPT_LIMIT', 3))}


def day_start():
    return utc_now().replace(hour=0, minute=0, second=0, microsecond=0)


def authorize(session, user_id, role=None):
    user = session.get(User, user_id)
    actual = Access.role(user)
    if not user or user.status != 'active' or actual not in {'teacher', 'admin'} or (role and role != actual):
        raise RagRuntimeError('当前账号无权访问课程问答请求', 403, 'access_changed')
    return actual


def validate_evidence(session, user_id, refs):
    if not refs:
        return
    rows = Access.chunks(user_id, session=session).filter(KnowledgeChunk.chunk_id.in_([r['chunk_id'] for r in refs])).all()
    current = {(r.chunk_id, r.document_id, r.version, hashlib.sha256(r.content.encode()).hexdigest()) for r in rows}
    if any((r['chunk_id'], r['document_id'], r['version'], r['content_hash']) not in current for r in refs):
        raise RagRuntimeError('课程材料已更新或访问范围已变化，请重新提问', 409, 'sources_changed')


def evidence_refs(plan):
    # Admin debug exposes candidates too, including those not selected for the prompt.
    chunks = [*plan.chunks, *(plan.retrieval.candidates if plan.debug else [])]
    refs = {c.chunk_id: {'chunk_id': c.chunk_id, 'document_id': c.document_id, 'version': c.version,
                         'content_hash': hashlib.sha256(c.content.encode()).hexdigest()} for c in chunks}
    return list(refs.values())


def claim(user_id, role, request_id, body_hash):
    with admission_lock('rag'):
        now = utc_now()
        authorize(db.session, user_id, role)
        row = db.session.get(Request, request_id)
        if row and row.user_id != user_id:
            raise RagRuntimeError('课程问答请求不存在', 404, 'not_found')
        if row and (row.body_hash != body_hash or row.role != role or row.policy_version != POLICY):
            raise RagRuntimeError('请求编号已用于其他内容或策略，请重新发起提问', 409, 'request_conflict')
        if row and row.status == 'complete':
            return {'request_id': request_id, 'replay': True}
        if row and row.status == 'processing' and row.lease_until > now:
            raise RagRuntimeError('该请求仍在处理，可稍后恢复结果', 409, 'request_in_progress')
        cap = limits()
        active = select(func.count()).select_from(Attempt).where(Attempt.status == 'processing', Attempt.lease_until > now)
        if db.session.scalar(active.where(Attempt.user_id == user_id)) >= cap['concurrency_limit'] or db.session.scalar(active) >= cap['global_concurrency']:
            raise RagRuntimeError('课程问答当前繁忙，请稍后重试', 429, 'capacity_reached')
        used = db.session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id, Attempt.started_at >= day_start()))
        if used >= cap['request_limit']:
            raise RagRuntimeError('本周期课程问答额度已用完', 429, 'daily_limit')
        tries = db.session.scalar(select(func.count()).select_from(Attempt).where(Attempt.request_id == request_id))
        if tries >= cap['attempt_limit']:
            raise RagRuntimeError('本次问答已达到重试上限，请重新提问', 429, 'attempt_limit')
        token = str(uuid.uuid4())
        until = now + timedelta(seconds=LEASE_SECONDS)
        if row is None:
            row = Request(id=request_id, user_id=user_id, role=role, body_hash=body_hash, policy_version=POLICY)
            db.session.add(row)
        row.status, row.lease_token, row.lease_until = 'processing', token, until
        row.error_code, row.completed_at = None, None
        db.session.flush()
        db.session.add(Attempt(id=token, request_id=request_id, user_id=user_id, lease_until=until))
        db.session.commit()
        return {'request_id': request_id, 'token': token, 'user_id': user_id, 'role': role}


def checkpoint(claimed, refs):
    with Session(db.engine) as session:
        row = session.get(Request, claimed['request_id'])
        if not row or row.status != 'processing' or row.lease_token != claimed['token'] or row.lease_until <= utc_now():
            raise RagRuntimeError('该请求已过期，请恢复状态后重试', 409, 'lease_expired')
        authorize(session, claimed['user_id'], claimed['role'])
        validate_evidence(session, claimed['user_id'], refs)


def finish(claimed, answer, refs):
    # Roll back retrieval/log read snapshots before an independent completion transaction.
    db.session.rollback()
    with Session(db.engine) as session:
        authorize(session, claimed['user_id'], claimed['role'])
        validate_evidence(session, claimed['user_id'], refs)
        updated = session.execute(update(Request).where(Request.id == claimed['request_id'],
            Request.lease_token == claimed['token'], Request.status == 'processing', Request.lease_until > utc_now())
            .values(status='complete', response=asdict(answer), evidence_refs=refs, completed_at=utc_now()))
        if updated.rowcount != 1:
            raise RagRuntimeError('该请求已过期，旧结果未发布', 409, 'lease_expired')
        session.execute(update(Attempt).where(Attempt.id == claimed['token']).values(status='complete', finished_at=utc_now()))
        session.commit()


def fail(claimed, reason):
    db.session.rollback()
    with Session(db.engine) as session:
        session.execute(update(Request).where(Request.id == claimed['request_id'], Request.lease_token == claimed['token'],
            Request.status == 'processing').values(status='failed', error_code=reason, completed_at=utc_now()))
        session.execute(update(Attempt).where(Attempt.id == claimed['token'], Attempt.status == 'processing')
            .values(status='failed', finished_at=utc_now()))
        session.commit()


def restore(user_id, request_id):
    request_id = request_uuid(request_id)
    with Session(db.engine) as session:
        role = authorize(session, user_id)
        row = session.get(Request, request_id)
        if not row or row.user_id != user_id:
            raise RagRuntimeError('课程问答请求不存在', 404, 'not_found')
        if row.role != role or row.policy_version != POLICY:
            raise RagRuntimeError('当前身份或问答策略已变化，请重新提问', 409, 'access_changed')
        expired = row.status == 'processing' and row.lease_until <= utc_now()
        attempts = session.scalar(select(func.count()).select_from(Attempt).where(Attempt.request_id == request_id))
        payload = {'request_id': request_id, 'status': 'expired' if expired else row.status,
                   'attempts_remaining': max(0, limits()['attempt_limit'] - attempts), 'answer': None}
        if row.status == 'complete':
            validate_evidence(session, user_id, row.evidence_refs)
            answer = RagAnswer(**deepcopy(row.response))
            payload['answer'] = answer.to_dict(include_debug=role == 'admin' and answer.debug is not None)
        return payload


def replay(user_id, request_id):
    # Same public shape as a fresh answer. Private references never leave storage.
    result = restore(user_id, request_id)
    data = result['answer']
    if data is None:
        raise RagRuntimeError('该请求仍在处理，可稍后恢复结果', 409, 'request_in_progress')
    return RagAnswer(**data)


def ask(query, *, user_id, role, request_id=None, scene='chat', context=None, history=None, debug=False, use_llm=None):
    request_id = request_uuid(request_id) if request_id is not None else str(uuid.uuid4())
    debug = bool(debug and role == 'admin')
    body_hash = fingerprint({'query': query, 'scene': scene, 'context': context or {}, 'history': history or [],
                             'debug': debug, 'use_llm': use_llm})
    claimed = claim(user_id, role, request_id, body_hash)
    if claimed.get('replay'):
        return replay(user_id, request_id)
    try:
        with scope(workflow='rag', user_id=user_id, request_id=request_id, attempt_id=claimed['token'],
                   policy_version=POLICY, retrieval_config_hash=fingerprint(retrieval_config())):
            service = KnowledgeRagService()
            plan = service.prepare(query, user_id=user_id, role=role, scene=scene, context=context, debug=debug)
            refs = evidence_refs(plan)
            db.session.rollback()
            checkpoint(claimed, refs)
            update_scope(stage='generation', state_version=plan.learner.state_version)
            if plan.blocked_reason:
                answer = service.finalize(plan, answer_text=None, generation_mode='refused', status='blocked', error=plan.blocked_reason)
            else:
                text, mode, meta = service.generate(plan, history=history, use_llm=use_llm)
                checkpoint(claimed, refs)
                answer = service.finalize(plan, answer_text=text, generation_mode=mode, model=meta.get('model'),
                    provider=meta.get('provider'), token_usage=meta.get('token_usage') or {})
            answer.request_id = request_id
            finish(claimed, answer, refs)
        # A fresh check after publication uses the same authorization as recovery.
        return replay(user_id, request_id)
    except Exception as exc:
        fail(claimed, exc.reason if isinstance(exc, RagRuntimeError) else 'generation_failed')
        raise


def usage(user_id):
    start, now, cap = day_start(), utc_now(), limits()
    with Session(db.engine) as session:
        authorize(session, user_id)
        used = session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id, Attempt.started_at >= start))
        active = session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id, Attempt.status == 'processing', Attempt.lease_until > now))
    return {'scope': 'rag', 'period_start': start.isoformat() + 'Z', 'reset_at': (start + timedelta(days=1)).isoformat() + 'Z',
            'request_limit': cap['request_limit'], 'requests_used': used, 'requests_remaining': max(0, cap['request_limit'] - used),
            'concurrency_limit': cap['concurrency_limit'], 'active_requests': active, 'attempt_limit': cap['attempt_limit']}
