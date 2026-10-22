"""One writer for learning projections. Business transactions append evidence only.

Policy v2 is an explicit heuristic, not calibrated knowledge tracing. Hint requests,
self-reported review scores and client test cases never change ability estimates.
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.base import db
from app.models.learner_state import (
    LearningEvent, LearnerState, LearnerConceptState, LearnerStateChange, TutorDisplayReceipt,
)
from app.utils.time import utc_now

POLICY = 'evidence-heuristic-v2'
KINDS = {'submission_graded', 'hint_displayed', 'review_recorded', 'review_due', 'session_start', 'misconception_reviewed', 'counterexample_checked'}
MODES = {'explain_error', 'review_approach', 'next_step', 'pseudocode', 'legacy_hint', 'concept_explain', 'algorithm_validation', 'algorithm_trace'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _insert_once(session, model, values, keys):
    """Portable conflict-safe insert without an implicit commit or transaction rollback."""
    if session.get_bind().dialect.name == 'mysql':
        from sqlalchemy.dialects.mysql import insert
        stmt = insert(model).values(**values)
        stmt = stmt.on_duplicate_key_update(**{keys[0]: getattr(stmt.inserted, keys[0])})
    else:
        from sqlalchemy.dialects.sqlite import insert
        stmt = insert(model).values(**values).on_conflict_do_nothing(index_elements=keys)
    session.execute(stmt)


class LearnerStateService:
    @staticmethod
    def append(*, user_id, kind, source_type, source_id, source_version, payload,
               course='python', occurred_at=None):
        """Internal producer API. Caller must commit its business row in this transaction."""
        if kind not in KINDS or course != 'python':
            raise ValueError('学习事件类型或课程无效')
        from app.data.knowledge_node_registry import resolve_node_id
        payload = dict(payload)
        if isinstance(payload.get('concept_id'), str):
            payload['concept_id'] = resolve_node_id(payload['concept_id']) or payload['concept_id']
        key = fingerprint([user_id, course, kind, source_type, str(source_id), str(source_version)])
        _insert_once(db.session, LearningEvent, dict(
            user_id=user_id, course=course, kind=kind, dedupe_key=key,
            source_type=source_type, source_id=str(source_id), source_version=str(source_version),
            payload=payload, occurred_at=occurred_at or utc_now(), status='pending', attempts=0,
        ), ['dedupe_key'])
        return db.session.scalar(select(LearningEvent).where(LearningEvent.dedupe_key == key))

    @staticmethod
    def record_submission(user_id, question, progress, grade_result):
        """Immutable snapshot of a server-graded formal assignment; never accepts browser tests."""
        if progress.status != 'completed' or progress.is_correct is None or not progress.answered_at:
            raise ValueError('正式判题尚未完成')
        displayed = db.session.scalar(select(TutorDisplayReceipt.id).where(
            TutorDisplayReceipt.user_id == user_id,
            TutorDisplayReceipt.question_id == question.id,
            TutorDisplayReceipt.displayed_at.is_not(None),
            TutorDisplayReceipt.displayed_at <= progress.answered_at,
        ).limit(1))
        # Hash includes server-owned question, answer and tests; hidden material never leaves this service.
        version = fingerprint([question.stem, question.correct_index, question.coding_meta(), question.knowledge_key])
        from app.services.misconception_policy import detect_signals
        from app.models import Trial
        trial = db.session.get(Trial, question.trial_id)
        return LearnerStateService.append(
            user_id=user_id, kind='submission_graded', source_type='trial_question_progress',
            source_id=progress.id, source_version='1', occurred_at=progress.answered_at,
            payload={'concept_id': question.knowledge_key or 'unclassified', 'question_id': question.id,
                     'class_id': trial.class_id if trial else None, 'trial_id': question.trial_id,
                     'question_title': question.stem[:120], 'question_version': version,
                     'code_hash': fingerprint(progress.submitted_code) if progress.submitted_code else None,
                     'correct': bool(progress.is_correct), 'assisted': bool(displayed),
                     'diagnostic_signals': detect_signals(progress.submitted_code, grade_result),
                     'evidence_scope': 'server_graded', 'backend': grade_result.get('execution_backend', 'answer_key'),
                     'passed_count': grade_result.get('passed_count'), 'test_count': grade_result.get('total')})

    @staticmethod
    def issue_receipt(user_id, *, text, mode, concept_id=None, question_id=None):
        if mode not in MODES | {'conversation'} or not text:
            raise ValueError('提示尚未生成')
        receipt = TutorDisplayReceipt(id=str(uuid.uuid4()), user_id=user_id, course='python',
            question_id=question_id, concept_id=concept_id, mode=mode, response_hash=fingerprint(text))
        db.session.add(receipt)
        db.session.flush()
        return receipt.id

    @staticmethod
    def acknowledge_hint(user_id, receipt_id):
        now = utc_now()
        changed = db.session.execute(update(TutorDisplayReceipt).where(
            TutorDisplayReceipt.id == receipt_id, TutorDisplayReceipt.user_id == user_id,
            TutorDisplayReceipt.displayed_at.is_(None),
        ).values(displayed_at=now).execution_options(synchronize_session=False)).rowcount
        row = db.session.scalar(select(TutorDisplayReceipt).where(
            TutorDisplayReceipt.id == receipt_id, TutorDisplayReceipt.user_id == user_id
        ).execution_options(populate_existing=True).with_for_update())
        if not row:
            db.session.rollback()
            raise LookupError('提示不存在')
        if changed and row.mode != 'conversation':
            LearnerStateService.append(user_id=user_id, kind='hint_displayed', source_type='tutor_response',
                source_id=row.id, source_version='1', occurred_at=row.displayed_at,
                payload={'concept_id': row.concept_id, 'question_id': row.question_id, 'mode': row.mode,
                         'evidence_scope': 'display_acknowledgement'})
        db.session.commit()
        return {'acknowledged': True, 'receipt_id': row.id}

    @staticmethod
    def record_review(user_id, row, schedule, now):
        LearnerStateService.append(user_id=user_id, kind='review_recorded', source_type='mistake_review',
            source_id=row.id, source_version=fingerprint(schedule), occurred_at=now,
            payload={'concept_id': row.knowledge_key, 'due_at': schedule.get('due_at'),
                     'evidence_scope': 'self_report', 'schedule': schedule})

    @staticmethod
    def _eligible(now):
        return or_(and_(LearningEvent.status == 'pending', or_(
            LearningEvent.retry_at.is_(None), LearningEvent.retry_at <= now)),
            and_(LearningEvent.status == 'processing', LearningEvent.lease_until < now))

    @staticmethod
    def claim():
        """An expiring durable lease makes process death recoverable across workers."""
        now, token = utc_now(), str(uuid.uuid4())
        with Session(db.engine) as session:
            ids = session.scalars(select(LearningEvent.id).where(
                LearnerStateService._eligible(now)).order_by(LearningEvent.id).limit(16)).all()
            session.rollback()  # End MySQL repeatable-read snapshot before claiming.
            for event_id in ids:
                changed = session.execute(update(LearningEvent).where(
                    LearningEvent.id == event_id, LearnerStateService._eligible(now)
                ).values(status='processing', lease_token=token, lease_until=now + timedelta(seconds=30),
                         attempts=LearningEvent.attempts + 1).execution_options(synchronize_session=False)).rowcount
                session.commit()
                if changed:
                    return event_id, token
        return None

    @staticmethod
    def propose(event, base_version):
        payload = event.payload or {}
        if event.kind == 'submission_graded' and (
            event.source_type not in {'trial_question_progress', 'practice_attempt'} or payload.get('evidence_scope') != 'server_graded'
            or type(payload.get('correct')) is not bool or type(payload.get('assisted')) is not bool
        ):
            raise ValueError('untrusted_submission')
        if event.kind == 'hint_displayed' and event.source_type != 'tutor_response':
            raise ValueError('untrusted_hint')
        if event.kind == 'counterexample_checked' and (
            event.source_type != 'counterexample_attempt' or payload.get('evidence_scope') != 'isolated_counterexample'
            or any(type(payload.get(key)) is not bool for key in ('counterexample_found','expected_output_correct','success'))
            or payload['success'] != (payload['counterexample_found'] and payload['expected_output_correct'])
            or type(payload.get('challenge_revision')) is not int or payload['challenge_revision'] < 1
            or not isinstance(payload.get('challenge_id'), str) or len(payload['challenge_id']) != 36
        ):
            raise ValueError('untrusted_counterexample')
        if event.kind == 'misconception_reviewed' and (
            event.source_type != 'teacher_review' or payload.get('evidence_scope') != 'teacher_review'
            or type(payload.get('reviewer_id')) is not int or type(payload.get('misconception_id')) is not int
            or type(payload.get('expected_revision')) is not int
            or payload.get('action') not in ('confirm', 'dismiss', 'reopen')
            or not isinstance(payload.get('note'), str) or not 1 <= len(payload['note'].strip()) <= 300
        ):
            raise ValueError('untrusted_review')
        concept = payload.get('concept_id')
        if concept is not None and (not isinstance(concept, str) or len(concept) > 80):
            raise ValueError('invalid_concept')
        reason = {
            'submission_graded': '服务端正式判题通过' if payload.get('correct') else '服务端正式判题未通过',
            'hint_displayed': '已展示辅导提示；不扣减能力估计',
            'review_recorded': '记录复习自评与下次时间；不作为测验成绩',
            'review_due': '复习已到期', 'session_start': '开始学习会话',
            'counterexample_checked': '已构造有效反例并核对预期输出；记录边界分析实践，不认定算法已掌握' if payload.get('success')
                else '反例实践已记录，仍需核对输入或预期输出；不降低正式掌握估计',
            'misconception_reviewed': '任课教师核对误概念候选：' + {'confirm': '确认', 'dismiss': '驳回', 'reopen': '重新观察'}.get(payload.get('action'), ''),
        }[event.kind]
        return {'base_version': base_version, 'evidence_ids': [event.id], 'producer_version': POLICY,
                'reason': reason, 'proposed_changes': {'kind': event.kind, 'concept_id': concept, 'payload': payload}}

    @staticmethod
    def _commit_proposal(session, state, event, proposal):
        # Reject unknown fields, fabricated evidence and stale proposals. No arbitrary model patching.
        expected = LearnerStateService.propose(event, state.version)
        if proposal != expected:
            raise ValueError('invalid_or_stale_proposal')
        changed = session.execute(update(LearnerState).where(
            LearnerState.id == state.id, LearnerState.version == proposal['base_version']
        ).values(version=state.version + 1, policy_version=POLICY, updated_at=utc_now())
            .execution_options(synchronize_session=False)).rowcount
        if changed != 1:
            raise ValueError('state_version_conflict')
        concept_id = proposal['proposed_changes']['concept_id']
        payload = event.payload
        if concept_id:
            concept = session.scalar(select(LearnerConceptState).where(
                LearnerConceptState.state_id == state.id, LearnerConceptState.concept_id == concept_id))
            if concept is None:
                concept = LearnerConceptState(state_id=state.id, concept_id=concept_id,
                    independent_count=0, independent_success=0, assisted_count=0,
                    assisted_success=0, hints_seen=0, review_count=0, counterexample_count=0, counterexample_success=0)
                session.add(concept)
            if event.kind == 'submission_graded':
                prefix = 'assisted' if payload['assisted'] else 'independent'
                setattr(concept, prefix + '_count', getattr(concept, prefix + '_count') + 1)
                if payload['correct']:
                    setattr(concept, prefix + '_success', getattr(concept, prefix + '_success') + 1)
                concept.last_evidence_at = max(concept.last_evidence_at or event.occurred_at, event.occurred_at)
                if (payload['correct'] and not payload['assisted'] and concept.counterexample_last_success_at
                        and event.occurred_at >= concept.counterexample_last_success_at):
                    concept.counterexample_review_due_at = None
            elif event.kind == 'counterexample_checked':
                concept.counterexample_count += 1
                if payload['success']:
                    concept.counterexample_success += 1
                    if not concept.counterexample_last_success_at or event.occurred_at >= concept.counterexample_last_success_at:
                        concept.counterexample_last_success_at = event.occurred_at
                        # A one-day transfer-practice reminder, not an SM-2 score or ability update.
                        later = session.scalars(select(LearningEvent).where(LearningEvent.user_id == event.user_id,
                            LearningEvent.kind == 'submission_graded', LearningEvent.status == 'done',
                            LearningEvent.occurred_at >= event.occurred_at)).all()
                        completed = any(e.payload.get('concept_id') == concept_id and e.payload.get('correct') is True
                            and e.payload.get('assisted') is False for e in later)
                        next_due = (event.occurred_at+timedelta(days=1)).isoformat()
                        concept.counterexample_review_due_at = None if completed else min(concept.counterexample_review_due_at or next_due, next_due)
            elif event.kind == 'hint_displayed':
                concept.hints_seen += 1
            elif event.kind == 'review_recorded':
                concept.review_count += 1
                if not concept.review_updated_at or event.occurred_at >= concept.review_updated_at:
                    concept.review_due_at = payload.get('due_at')
                    concept.review_updated_at = event.occurred_at
            elif event.kind == 'review_due' and not concept.review_updated_at:
                # Import an existing due schedule without inventing recall scores.
                concept.review_due_at = payload.get('due_at')
        from app.services.misconception_policy import MisconceptionPolicy
        MisconceptionPolicy.apply(session, state, event, state.version + 1)
        session.add(LearnerStateChange(state_id=state.id, event_id=event.id,
            base_version=state.version, version=state.version + 1, producer_version=POLICY,
            reason=proposal['reason'], changes=proposal['proposed_changes']))
        event.status, event.processed_at = 'done', utc_now()
        event.lease_token = event.lease_until = event.error_code = None

    @staticmethod
    def process_claim(event_id, token):
        # No model I/O under a transaction. Deterministic v1 reducer only.
        for attempt in range(4):
            try:
                with Session(db.engine) as session:
                    event = session.scalar(select(LearningEvent).where(
                        LearningEvent.id == event_id, LearningEvent.status == 'processing',
                        LearningEvent.lease_token == token, LearningEvent.lease_until > utc_now()
                    ).with_for_update())
                    if not event:
                        return False
                    _insert_once(session, LearnerState, dict(user_id=event.user_id, course=event.course,
                        version=0, policy_version=POLICY), ['user_id', 'course'])
                    state = session.scalar(select(LearnerState).where(
                        LearnerState.user_id == event.user_id, LearnerState.course == event.course
                    ).with_for_update())
                    proposal = LearnerStateService.propose(event, state.version)
                    LearnerStateService._commit_proposal(session, state, event, proposal)
                    session.commit()
                    return True
            except (IntegrityError, OperationalError):
                if attempt < 3:
                    continue  # New transaction/snapshot; recompute, never replay an old delta.
                error = 'database_conflict'
            except (ValueError, KeyError, TypeError):
                error = 'invalid_evidence'
                break
        with Session(db.engine) as session:
            event = session.scalar(select(LearningEvent).where(
                LearningEvent.id == event_id, LearningEvent.lease_token == token).with_for_update())
            if event:
                event.status = 'failed' if error == 'invalid_evidence' or event.attempts >= 8 else 'pending'
                event.error_code = error
                event.retry_at = utc_now() + timedelta(seconds=min(300, 2 ** event.attempts))
                event.lease_token = event.lease_until = None
                session.commit()
        return False

    @staticmethod
    def drain(limit=50):
        count = 0
        for _ in range(limit):
            claim = LearnerStateService.claim()
            if not claim:
                break
            count += int(LearnerStateService.process_claim(*claim))
        return count

    @staticmethod
    def snapshot(user_id, *, session=None):
        # Resource creation can supply its own repeatable transaction so profile and state agree.
        if session is not None:
            return LearnerStateService._snapshot(session, user_id)
        # Own repeatable snapshot, independent of the request's earlier ORM reads.
        # Python sqlite's legacy SELECT mode needs explicit BEGIN for multiple reads.
        with Session(db.engine) as session:
            if session.get_bind().dialect.name == 'sqlite':
                session.connection().exec_driver_sql('BEGIN')
            elif session.get_bind().dialect.name == 'mysql':
                session.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
            return LearnerStateService._snapshot(session, user_id)

    @staticmethod
    def _snapshot(session, user_id):
        from app.data.knowledge_node_registry import get_entry, resolve_node_id
        state_rows = session.execute(select(LearnerState, LearnerConceptState).outerjoin(
            LearnerConceptState, LearnerConceptState.state_id == LearnerState.id
        ).where(LearnerState.user_id == user_id, LearnerState.course == 'python')
            .order_by(LearnerConceptState.concept_id).execution_options(populate_existing=True)).all()
        state = state_rows[0][0] if state_rows else None
        concepts = []
        for _, row in state_rows:
            if row is None:
                continue
            weight = row.independent_count + .5 * row.assisted_count
            estimate = (1 + row.independent_success + .5 * row.assisted_success) / (2 + weight) if weight else None
            entry = get_entry(resolve_node_id(row.concept_id) or row.concept_id)
            concepts.append({'concept_id': row.concept_id, 'estimate': round(estimate, 4) if estimate is not None else None,
                'label': entry.label if entry else row.concept_id,
                'estimate_method': POLICY, 'uncertainty': round(1 / math.sqrt(1 + weight), 4),
                'uncertainty_method': 'evidence_count_proxy', 'independent_count': row.independent_count,
                'independent_success': row.independent_success, 'assisted_count': row.assisted_count,
                'assisted_success': row.assisted_success, 'hints_seen': row.hints_seen,
                'counterexample_count': row.counterexample_count, 'counterexample_success': row.counterexample_success,
                'counterexample_review_due_at': row.counterexample_review_due_at,
                'review_count': row.review_count, 'review_due_at': row.review_due_at,
                'last_evidence_at': row.last_evidence_at.isoformat() if row.last_evidence_at else None,
                'stale': bool(row.last_evidence_at and row.last_evidence_at < utc_now() - timedelta(days=30))})
        rows = session.execute(select(LearnerStateChange, LearningEvent).join(
            LearningEvent, LearningEvent.id == LearnerStateChange.event_id).where(
            LearnerStateChange.state_id == state.id if state else False,
            LearnerStateChange.version <= state.version if state else False,
        ).order_by(LearnerStateChange.version.desc()).limit(20)).all()
        pending = session.scalar(select(db.func.count()).select_from(LearningEvent).where(
            LearningEvent.user_id == user_id, LearningEvent.status.in_(['pending', 'processing'])))
        failed = session.scalar(select(db.func.count()).select_from(LearningEvent).where(
            LearningEvent.user_id == user_id, LearningEvent.status == 'failed'))
        from app.services.misconception_policy import MisconceptionPolicy
        from app.services.learning_evidence import public_change
        return {'course': 'python', 'state_version': state.version if state else 0, 'policy_version': POLICY,
            'estimate_disclaimer': '基于正式作答证据的启发式估计，未经概率校准；没有证据时尚待了解。',
            'pending_events': pending, 'failed_events': failed, 'concepts': concepts,
            'misconceptions': MisconceptionPolicy.serialize(session, state.id) if state else [],
            'changes': [public_change(c, e) for c, e in rows]}
