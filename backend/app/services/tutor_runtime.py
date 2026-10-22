"""Shared database limits and cancellation survive tabs, workers and restarts."""
import math
import time
import uuid
from datetime import timedelta
from flask import current_app
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import db
from app.models.ai_runtime import AiRuntimeLock, TutorRequestAttempt as Attempt, TutorRequestCancellation as Cancellation, AiModelCall as Call
from app.models.tutor_session import TutorTurn, TutorSession
from app.services.tutor_context import TutorContextError
from app.services.model_observation import observe_model
from app.services.learner_state import fingerprint
from app.services.knowledge.settings import retrieval_config
from app.utils.time import utc_now


def limits():
    return {'daily_requests': max(1, int(current_app.config.get('TUTOR_DAILY_REQUEST_LIMIT', 80))),
            'user_concurrency': max(1, int(current_app.config.get('TUTOR_USER_CONCURRENCY', 2))),
            'global_concurrency': max(1, int(current_app.config.get('TUTOR_GLOBAL_CONCURRENCY', 8))),
            'retry_attempts': max(1, int(current_app.config.get('TUTOR_REQUEST_ATTEMPT_LIMIT', 3)))}


def day_start():
    return utc_now().replace(hour=0, minute=0, second=0, microsecond=0)


def capacity_lock():
    # No existing snapshot before acquiring this single short database lock.
    db.session.rollback()
    try:
        with db.session.begin_nested():
            db.session.add(AiRuntimeLock(scope='tutor', revision=0)); db.session.flush()
    except IntegrityError:
        pass
    db.session.execute(update(AiRuntimeLock).where(AiRuntimeLock.scope=='tutor').values(revision=AiRuntimeLock.revision+1))


def check_cancelled(user_id, request_id):
    if db.session.get(Cancellation, (user_id, request_id)):
        raise TutorContextError('本次请求已取消，请重新发起提问', 409)


def reserve(user_id, claim, until):
    cap=limits(); now=utc_now()
    active=select(func.count()).select_from(Attempt).where(Attempt.status=='processing',Attempt.lease_until>now)
    if db.session.scalar(active.where(Attempt.user_id==user_id))>=cap['user_concurrency']:
        raise TutorContextError('已有请求正在处理或收尾，请稍后再试',429)
    if db.session.scalar(active)>=cap['global_concurrency']:
        raise TutorContextError('小 E 当前繁忙，请稍后重试',429)
    used=db.session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id==user_id,Attempt.started_at>=day_start()))
    if used>=cap['daily_requests']:
        raise TutorContextError('本周期辅导额度已用完，请在额度恢复后再试',429)
    attempts=db.session.scalar(select(func.count()).select_from(Attempt).where(Attempt.request_id==claim['request_id']))
    if attempts>=cap['retry_attempts']:
        raise TutorContextError('本次请求已达到重试上限，请重新发起提问',429)
    db.session.add(Attempt(id=claim['token'],user_id=user_id,request_id=claim['request_id'],lease_until=until))


def checkpoint(claim):
    with Session(db.engine) as session:
        row=session.get(TutorTurn,claim['request_id'])
        if not row or row.status!='processing' or row.lease_token!=claim['token'] or row.lease_until<=utc_now():
            raise TutorContextError('本次请求已取消或过期，请重新发起提问',409)


def settle(claim):
    with Session(db.engine) as session:
        row=session.get(TutorTurn,claim['request_id'])
        status='complete' if row and row.status=='complete' and row.lease_token==claim['token'] else 'cancelled' if row and row.status=='cancelled' else 'failed'
        session.execute(update(Attempt).where(Attempt.id==claim['token'],Attempt.status=='processing').values(status=status,finished_at=utc_now()))
        session.commit()


def cancel(user_id, request_id):
    from app.services.tutor_sessions import uuid_value
    request_id=uuid_value(request_id,'请求编号')
    capacity_lock()
    try:
        row=db.session.get(TutorTurn,request_id)
        if row and row.user_id!=user_id:
            raise TutorContextError('辅导请求不存在',404)
        if row and row.status=='complete':
            db.session.rollback()
            return {'request_id':request_id,'status':'complete','cancelled':False}
        if not db.session.get(Cancellation,(user_id,request_id)):
            db.session.add(Cancellation(user_id=user_id,request_id=request_id))
        if row:
            db.session.execute(update(TutorSession).where(TutorSession.id==row.session_id,TutorSession.lease_token==row.lease_token).values(lease_token=None,lease_until=None))
            row.status='cancelled';row.error_code='cancelled';row.completed_at=utc_now()
        db.session.commit()
        return {'request_id':request_id,'status':'cancelled','cancelled':True}
    except Exception:
        db.session.rollback();raise


def model_call(user_id, claim, teaching, stage, function):
    checkpoint(claim)
    from app.services.model_accounting import operation
    return operation({'workflow':'tutor','request_id':claim['request_id'],'attempt_id':claim['token'],'user_id':user_id,
        'stage':stage,'policy_version':teaching.policy_version,'state_version':teaching.state_version,
        'retrieval_config_hash':claim.get('retrieval_config_hash') or fingerprint(retrieval_config())},function)


def usage(user_id):
    start=day_start();now=utc_now();cap=limits()
    with Session(db.engine) as session:
        attempts=session.scalars(select(Attempt).where(Attempt.user_id==user_id,Attempt.started_at>=start)).all()
        calls=session.scalars(select(Call).where(Call.user_id==user_id,Call.workflow=='tutor',Call.started_at>=start)).all()
        active=session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id==user_id,Attempt.status=='processing',Attempt.lease_until>now))
        durations=sorted(r.elapsed_ms for r in calls if r.elapsed_ms is not None)
        reported=[r for r in calls if r.total_tokens is not None]
        return {'scope':'tutor','period_start':start.isoformat()+'Z','reset_at':(start+timedelta(days=1)).isoformat()+'Z',
                'request_limit':cap['daily_requests'],'requests_used':len(attempts),'requests_remaining':max(0,cap['daily_requests']-len(attempts)),
                'active_requests':active,'concurrency_limit':cap['user_concurrency'],'model_calls':len(calls),
                'reported_total_tokens':sum(r.total_tokens for r in reported),'unknown_usage_calls':len(calls)-len(reported),
                'failed_calls':sum(r.status=='failed' for r in calls),'cancelled_requests':sum(r.status=='cancelled' for r in attempts),
                'model_latency_ms':{'p50':durations[math.ceil(len(durations)*.5)-1] if durations else None,'p95':durations[math.ceil(len(durations)*.95)-1] if durations else None},
                'cost':None,'cost_status':'not_priced'}
