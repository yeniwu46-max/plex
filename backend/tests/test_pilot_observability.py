"""Evidence scope, missing outcomes, latency denominators and classroom privacy."""
from datetime import timedelta
import importlib.util
from pathlib import Path
from unittest.mock import patch
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from test_learner_state import app
from test_tutor_context import headers
from test_tutoring_modes import dependencies, Provider, candidate, ask, body
from app.models import db, User, Class, Trial, TrialQuestion, TrialQuestionProgress
from app.models.ai_runtime import AiModelCall, TutorRequestAttempt
from app.models.learner_state import TutorDisplayReceipt, LearningEvent
from app.models.tutor_session import TutorSession, TutorTurn
from app.services.learner_state import LearnerStateService as State
from app.services.pilot_observability import snapshot
from app.services.tutor_context import TutorContextError
from app.data.knowledge_node_registry import resolve_node_id
from app.utils.time import utc_now


def ids(app):
    uid = app.config['TEST_STUDENT']
    return uid, db.session.get(User, uid).class_id, app.config['TEST_QUESTION']


def turn(app, when, *, status='complete', display=True, scoped=True, concept='loop', uid=None, mode='next_step'):
    default_uid, cls, qid = ids(app)
    uid = uid or default_uid
    sid, rid, lease = (str(uuid.uuid4()) for _ in range(3))
    sess = TutorSession(id=sid, user_id=uid, question_ref=f'lc-{qid}', question_version='v1',
        class_id=cls if scoped else None, formal_question_id=qid if scoped else None,
        concept_id=resolve_node_id(concept) or concept, created_at=when)
    db.session.add(sess); db.session.flush()
    receipt = None
    if status == 'complete':
        receipt = TutorDisplayReceipt(id=str(uuid.uuid4()), user_id=uid, question_id=qid,
            concept_id=concept, mode=mode, response_hash='private-hash', created_at=when+timedelta(seconds=1),
            displayed_at=when+timedelta(seconds=2) if display else None)
        db.session.add(receipt); db.session.flush()
    row = TutorTurn(id=rid, session_id=sid, user_id=uid, request_hash='hash', code_hash='hash',
        question='DO NOT EXPOSE PRIVATE QUESTION', mode=mode, status=status,
        lease_token=lease, lease_until=when+timedelta(seconds=120), created_at=when,
        completed_at=when+timedelta(seconds=1) if status=='complete' else None,
        receipt_id=receipt.id if receipt else None, response={'summary':'DO NOT EXPOSE MODEL ANSWER'})
    db.session.add(row); db.session.flush()
    return row


def grade(app, when, *, correct=True, assisted=False, concept='loop', question_id=None, frozen=True):
    uid, cls, qid = ids(app)
    if question_id is None:
        original = db.session.get(TrialQuestion, qid)
        q = TrialQuestion(trial_id=original.trial_id, stem='Synthetic follow-up', options=['A','B'],
            correct_index=0, knowledge_key=concept)
        db.session.add(q); db.session.flush()
    else:
        q = db.session.get(TrialQuestion, question_id)
    progress = TrialQuestionProgress.query.filter_by(user_id=uid, question_id=q.id).first()
    if not progress:
        progress = TrialQuestionProgress(user_id=uid, question_id=q.id)
        db.session.add(progress)
    progress.status, progress.is_correct, progress.answered_at = 'completed', correct, when
    if assisted:
        db.session.add(TutorDisplayReceipt(id=str(uuid.uuid4()), user_id=uid, question_id=q.id,
            concept_id=concept, mode='next_step', response_hash='hash',
            created_at=when-timedelta(seconds=2), displayed_at=when-timedelta(seconds=1)))
    db.session.flush()
    event = State.record_submission(uid, q, progress, {})
    if not frozen:
        payload = dict(event.payload); payload.pop('class_id'); event.payload = payload
    db.session.flush()
    return event


def report(app, now, days=14):
    db.session.commit()
    cls = ids(app)[1]
    with patch('app.services.pilot_observability.utc_now', return_value=now):
        return snapshot(app.config['TEST_TEACHER'], cls, days)


def test_pilot_empty_has_no_fabricated_results_or_latency(app):
    with app.app_context():
        result = report(app, utc_now())
        assert result['flow']['requests'] == result['followup']['observed'] == 0
        assert result['current_students'] == 1 and result['tutoring_students'] == 0
        assert result['latency_ms']['completed_request'] == {'samples':0,'missing':0,'p50':None,'p95':None}


def test_pilot_scope_is_captured_by_actual_tutoring_and_grading(app, dependencies):
    payload = body(app, 'next_step')
    response = ask(app, payload, Provider(candidate()))
    assert response.status_code == 200
    with app.app_context():
        uid, cls, qid = ids(app)
        session = TutorSession.query.one()
        assert (session.class_id, session.formal_question_id, session.concept_id) == (cls, qid, resolve_node_id('loop'))
        event = grade(app, utc_now()-timedelta(seconds=1))
        assert event.payload['class_id'] == cls
        db.session.commit()
        State.acknowledge_hint(uid, response.json['data']['display_receipt_id'])
        result = report(app, utc_now()+timedelta(seconds=1))
        assert result['flow']['requests'] == result['flow']['display_confirmed'] == 1
        assert result['formal_practice']['total'] == 1


def test_pilot_repeated_hints_use_first_followup_not_best_followup(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        turn(app, now-timedelta(days=10))
        turn(app, now-timedelta(days=9))
        grade(app, now-timedelta(days=8), correct=False)
        grade(app, now-timedelta(days=7), correct=True)
        result = report(app, now)
        assert result['flow']['display_confirmed'] == 2
        assert result['followup'] == {'unit':'student_concept_first_display','days':7,'exposures':1,
            'observed':1,'first_correct':0,'first_incorrect':1,'window_open':0,'window_closed_without_observation':0}
        assert result['formal_practice']['independent'] == 2
        assert result['formal_practice']['independent_correct'] == 1


def test_pilot_missing_outcome_distinguishes_open_and_closed_windows(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        turn(app, now-timedelta(days=10), concept='loop')
        turn(app, now-timedelta(days=2), concept='var')
        result = report(app, now)
        assert result['followup']['exposures'] == 2
        assert result['followup']['window_open'] == result['followup']['window_closed_without_observation'] == 1
        assert result['followup']['first_incorrect'] == 0


def test_pilot_same_question_assisted_early_late_other_concept_do_not_count_as_followup(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        when = now-timedelta(days=10)
        turn(app, when)
        grade(app, when-timedelta(hours=1))
        grade(app, when+timedelta(days=1), question_id=ids(app)[2])
        grade(app, when+timedelta(days=2), assisted=True)
        grade(app, when+timedelta(days=3), concept='var')
        grade(app, when+timedelta(days=8))
        result = report(app, now)
        assert result['followup']['observed'] == 0
        assert result['formal_practice']['assisted'] == 2
        assert result['formal_practice']['independent'] == 3


def test_pilot_generation_conversation_no_ack_and_unknown_concept_are_distinct(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        turn(app, now-timedelta(days=1), display=False)
        turn(app, now-timedelta(days=1), mode='conversation')
        turn(app, now-timedelta(days=1), concept=None)
        turn(app, now-timedelta(days=1), status='failed')
        turn(app, now-timedelta(days=1), status='cancelled')
        turn(app, now-timedelta(days=1), status='processing')
        turn(app, now-timedelta(seconds=1), status='processing')
        result = report(app, now)
        assert result['flow'] == {'requests':7,'states':{'complete':3,'failed':1,'cancelled':1,'expired':1,'processing':1},
                                  'published_help':2,'display_confirmed':1,'not_display_confirmed':1}
        assert result['followup']['exposures'] == 0


def test_pilot_historical_scope_is_not_backfilled_and_transfers_cannot_reattribute(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        turn(app, now-timedelta(days=1), scoped=False)
        grade(app, now-timedelta(hours=1), frozen=False)
        assert report(app, now)['flow']['requests'] == 0
        assert report(app, now)['formal_practice']['total'] == 0
        scoped = turn(app, now-timedelta(days=1))
        grade(app, now-timedelta(hours=1))
        uid, old_class, _ = ids(app)
        other_class = Class(name='Transferred', teacher_id=app.config['TEST_TEACHER'], grade_level=1)
        db.session.add(other_class); db.session.flush()
        db.session.get(User, uid).class_id = other_class.id
        db.session.commit()
        with patch('app.services.pilot_observability.utc_now', return_value=now):
            assert snapshot(app.config['TEST_TEACHER'], old_class)['flow']['requests'] == 0
            assert snapshot(app.config['TEST_TEACHER'], other_class.id)['flow']['requests'] == 0
            assert snapshot(app.config['TEST_TEACHER'], other_class.id)['formal_practice']['total'] == 0
        assert db.session.get(TutorSession, scoped.session_id).class_id == old_class


def test_pilot_frozen_or_changed_role_student_is_excluded(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        turn(app, now-timedelta(days=1))
        student = db.session.get(User, ids(app)[0])
        student.status = 'frozen'
        assert report(app, now)['current_students'] == 0
        student.status = 'active'; student.role_id = db.session.get(User, app.config['TEST_TEACHER']).role_id
        assert report(app, now)['flow']['requests'] == 0


def test_pilot_latency_counts_attempts_calls_missing_and_failures_separately(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        row = turn(app, now-timedelta(hours=1))
        for i, (state, ms) in enumerate([('succeeded',100),('failed',900),('succeeded',None),('processing',0)]):
            db.session.add(AiModelCall(id=str(uuid.uuid4()), workflow='tutor', request_id=row.id,
                attempt_id=row.lease_token, user_id=row.user_id, stage='review' if i else 'generation',
                status=state, policy_version='test', state_version=0, retrieval_config_hash='hash',
                elapsed_ms=ms, started_at=row.created_at, finished_at=None if state=='processing' else row.completed_at))
        db.session.add_all([
            TutorRequestAttempt(id=row.lease_token, user_id=row.user_id, request_id=row.id,
                status='failed', started_at=row.created_at-timedelta(seconds=3), finished_at=row.created_at,
                lease_until=row.lease_until),
            TutorRequestAttempt(id=str(uuid.uuid4()), user_id=row.user_id, request_id=row.id,
                status='processing', started_at=row.created_at, lease_until=row.lease_until),
        ])
        result = report(app, now)['latency_ms']
        assert result['completed_request']['p50'] == 1000
        assert result['finished_attempt']['p50'] == 3000
        assert result['finished_model_call'] == {'samples':2,'missing':1,'p50':100,'p95':900}
        assert result['model_by_status']['succeeded']['p95'] == 100
        assert result['model_by_status']['succeeded']['missing'] == 1
        assert result['unfinished_attempts'] == result['unfinished_model_calls'] == 1


def test_pilot_window_and_privacy_no_content_or_individual_identifiers(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        turn(app, now-timedelta(days=20)); turn(app, now-timedelta(days=2)); turn(app, now+timedelta(days=1))
        assert report(app, now, 7)['flow']['requests'] == 1
        result = report(app, now, 30)
        assert result['flow']['requests'] == 2
        payload = str(result)
        for private in ('PRIVATE QUESTION', 'MODEL ANSWER', 'private-hash', 'request_id', 'receipt_id', 'user_id', 'question_id'):
            assert private not in payload


def test_pilot_api_permissions_and_days_validation(app):
    with app.app_context():
        cls = ids(app)[1]
        other = Class(name='Other teacher', teacher_id=app.config['TEST_STUDENT'], grade_level=1)
        db.session.add(other); db.session.commit(); other_id = other.id
    client = app.test_client(); path = f'/api/v1/teacher/classes/{cls}/learning-observations'
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers(app)).status_code == 403
    assert client.get(path, headers=headers(app, True)).status_code == 200
    for invalid in ('0', '-1', '31', '7.0', 'seven', ''):
        assert client.get(path+'?days='+invalid, headers=headers(app, True)).status_code == 400
    assert client.get(f'/api/v1/teacher/classes/{other_id}/learning-observations', headers=headers(app, True)).status_code == 403


def test_pilot_over_limit_refuses_partial_analytics(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        turn(app, now-timedelta(days=1)); db.session.commit()
        from app.services.pilot_observability import _bounded
        from sqlalchemy import select
        with pytest.raises(TutorContextError) as caught:
            _bounded(db.session, select(TutorTurn.id), limit=0)
        assert caught.value.status == 422


def test_pilot_migration_is_repeatable_and_old_scopes_remain_null(app):
    with app.app_context():
        now = utc_now().replace(microsecond=0)
        row = turn(app, now-timedelta(days=1), scoped=False); db.session.commit()
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261018_0034_pilot_scope.py'
        spec = importlib.util.spec_from_file_location('pilot_migration', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with db.engine.begin() as conn:
            operations = Operations(MigrationContext.configure(conn))
            with patch.object(module, 'op', operations):
                module.downgrade(); module.upgrade(); module.upgrade()
            assert {c['name'] for c in inspect(conn).get_columns('tutor_sessions')} >= {'class_id','concept_id','formal_question_id'}
            values = conn.execute(text('SELECT class_id, formal_question_id, concept_id FROM tutor_sessions WHERE id=:id'), {'id':row.session_id}).one()
            assert tuple(values) == (None, None, None)
