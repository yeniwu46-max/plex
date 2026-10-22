"""Short transactional claims around slow model work; retry IDs keep one receipt."""
from copy import deepcopy
from datetime import timedelta
import uuid

from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError

from app.models import db, TrialQuestion, Trial, User
from app.models.tutor_session import TutorSession, TutorTurn
from app.models.learner_state import TutorDisplayReceipt
from app.services.knowledge import KnowledgeService
from app.services.counterexample_recommendation import refresh_response
from app.services.tutor_context import TutorContextError, TutorContextService
from app.services.learner_state import LearnerStateService
from app.utils.time import utc_now
from app.services import tutor_runtime as runtime

LEASE_SECONDS = 120


def uuid_value(value, field):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value.lower():
            raise ValueError()
        return value.lower()
    except (ValueError, AttributeError):
        raise TutorContextError(f'{field} 必须是 UUID') from None


class TutorSessions:
    @staticmethod
    def read_turn(user_id, request_id):
        row = db.session.get(TutorTurn, uuid_value(request_id, '请求编号'))
        if not row or row.user_id != user_id or row.status != 'complete':
            raise TutorContextError('辅导记录不存在或尚未完成', 404)
        session = db.session.get(TutorSession, row.session_id)
        context = TutorContextService.resolve(user_id, {'question_ref': session.question_ref})
        if (context.task or {}).get('version') != session.question_version:
            raise TutorContextError('原题目或辅导权限已变化，这条记录暂不能展示', 409)
        response, dependencies = deepcopy(row.response), deepcopy(row.evidence_refs)
        db.session.rollback()
        if not TutorContextService.current(user_id, context) or not KnowledgeService.tutor_sources_current(user_id, dependencies):
            raise TutorContextError('原课程材料或访问权限已变化，这条记录暂不能展示', 409)
        return refresh_response(user_id, response)

    @staticmethod
    def claim(user_id, request_id, session_id, digest, context, question, mode, *, lease_seconds=LEASE_SECONDS):
        """A session lease serializes hints; only the current claim may publish."""
        runtime.capacity_lock()
        now, token = utc_now(), str(uuid.uuid4())
        until = now + timedelta(seconds=lease_seconds)
        try:
            runtime.check_cancelled(user_id, request_id)
            turn = db.session.get(TutorTurn, request_id)
            if turn:
                if turn.user_id != user_id or turn.request_hash != digest:
                    raise TutorContextError('请求编号已使用，请重新发起提问', 409)
                session_id = turn.session_id
            session = db.session.get(TutorSession, session_id) if session_id else None
            if session_id and (not session or session.user_id != user_id):
                raise TutorContextError('辅导会话不存在', 404)
            if session and (session.question_ref != context.ref or session.question_version != (context.task or {}).get('version')):
                raise TutorContextError('题目已切换或更新，请开启新的辅导会话', 409)
            if turn and turn.status == 'complete':
                response = deepcopy(turn.response)
                dependencies = deepcopy(turn.evidence_refs)
                db.session.rollback()
                if not KnowledgeService.tutor_sources_current(user_id, dependencies):
                    raise TutorContextError('这条回答的材料已变更，请重新提问', 409)
                return {'cached': refresh_response(user_id, response)}
            if not session:
                scope = {}
                formal_id = (context.task or {}).get('formal_question_id')
                if formal_id:
                    q = db.session.get(TrialQuestion, formal_id)
                    trial = db.session.get(Trial, q.trial_id) if q else None
                    user = db.session.get(User, user_id)
                    if not trial or not user or user.class_id != trial.class_id:
                        raise TutorContextError('题目班级权限已变化，请刷新后重试', 409)
                    from app.data.knowledge_node_registry import resolve_node_id
                    scope = {'class_id': trial.class_id, 'formal_question_id': q.id,
                             'concept_id': resolve_node_id(q.knowledge_key) or q.knowledge_key}
                session = TutorSession(id=str(uuid.uuid4()), user_id=user_id, question_ref=context.ref,
                    question_version=(context.task or {}).get('version'), **scope)
                db.session.add(session); db.session.flush()
            sid = session.id
            if not db.session.execute(update(TutorSession).where(TutorSession.id == sid,
                    or_(TutorSession.lease_until.is_(None), TutorSession.lease_until <= now))
                    .values(lease_token=token, lease_until=until).execution_options(synchronize_session=False)).rowcount:
                raise TutorContextError('上一条提问仍在处理，请稍后使用原请求编号重试', 409)
            if turn:
                if not db.session.execute(update(TutorTurn).where(TutorTurn.id == request_id,
                        or_(TutorTurn.status == 'failed', TutorTurn.lease_until <= now))
                        .values(status='processing', lease_token=token, lease_until=until, error_code=None)
                        .execution_options(synchronize_session=False)).rowcount:
                    raise TutorContextError('提问仍在处理，请稍后重试', 409)
            else:
                db.session.add(TutorTurn(id=request_id, session_id=sid, user_id=user_id,
                    request_hash=digest, code_hash=context.code_hash, question=question, mode=mode,
                    status='processing', lease_token=token, lease_until=until))
            db.session.flush()
            claim = {'session_id': sid, 'request_id': request_id, 'token': token}
            runtime.reserve(user_id, claim, until)
            db.session.commit()
            return claim
        except IntegrityError:
            db.session.rollback()
            raise TutorContextError('相同请求正在处理，请稍后使用原请求编号重试', 409) from None
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def history(user_id, session_id):
        # Only acknowledged answers influence the next hint, not canceled output.
        rows = db.session.execute(select(TutorTurn.question, TutorTurn.response, TutorTurn.evidence_refs).join(
            TutorDisplayReceipt, TutorDisplayReceipt.id == TutorTurn.receipt_id).where(
            TutorTurn.user_id == user_id, TutorTurn.session_id == session_id, TutorTurn.status == 'complete',
            TutorDisplayReceipt.displayed_at.is_not(None)).order_by(TutorTurn.created_at.desc()).limit(6)).all()
        db.session.rollback()
        history = []
        for question, response, dependencies in reversed(rows):
            if KnowledgeService.tutor_sources_current(user_id, dependencies):
                history.append({'question': question[:1000], 'summary': response['summary'],
                    'next_step': response['next_step'], 'mode': response['mode'], 'records_at': response.get('records_at'),
                    'example': response.get('example'), 'trace_input': response.get('trace_input'),
                    'trace_steps': response.get('trace_steps'), 'trace_notice': response.get('trace_notice'),
                    'citations': response.get('citations', []),
                    'evidence_refs': dependencies})
        return history

    @staticmethod
    def finish(user_id, claim, response, context, *, count_help, dependencies, track_display=False):
        runtime.capacity_lock()
        runtime.check_cancelled(user_id, claim['request_id'])
        now = utc_now()
        # Lock/conditional-update the session before the turn, consistently with claim.
        changed = db.session.execute(update(TutorSession).where(
            TutorSession.id == claim['session_id'], TutorSession.lease_token == claim['token'],
            TutorSession.lease_until > now).values(lease_token=None, lease_until=None)
            .execution_options(synchronize_session=False)).rowcount
        if not changed:
            db.session.rollback()
            raise TutorContextError('本次请求已过期，请使用原请求编号重试', 409)
        row = db.session.get(TutorTurn, claim['request_id'], populate_existing=True)
        if row.lease_token != claim['token'] or row.status != 'processing':
            db.session.rollback()
            raise TutorContextError('本次请求已过期，请重试', 409)
        receipt = None
        if count_help or track_display:
            receipt = LearnerStateService.issue_receipt(user_id, text=response['summary'] + response['next_step'],
                mode=response['mode'] if count_help else 'conversation', concept_id=(context.task or {}).get('concept_id'),
                question_id=(context.task or {}).get('formal_question_id'))
        response = {**response, 'request_id': row.id, 'session_id': row.session_id, 'display_receipt_id': receipt}
        row.response, row.receipt_id, row.status, row.completed_at = response, receipt, 'complete', now
        row.evidence_refs = [{'chunk_id': s['chunk_id'], 'version': s['version'],
            **({'content_hash': s['content_hash']} if s.get('content_hash') else {})} for s in dependencies]
        db.session.commit()
        return response

    @staticmethod
    def fail(claim):
        db.session.rollback()
        db.session.execute(update(TutorSession).where(TutorSession.id == claim['session_id'],
            TutorSession.lease_token == claim['token']).values(lease_until=None, lease_token=None))
        db.session.execute(update(TutorTurn).where(TutorTurn.id == claim['request_id'],
            TutorTurn.lease_token == claim['token'], TutorTurn.status == 'processing')
            .values(status='failed', error_code='request_failed'))
        db.session.commit()
