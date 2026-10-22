"""Real SQLite transactions, durable recovery and evidence/access boundaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
import os
import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from app.config import TestingConfig, DevelopmentConfig
from app.models import db, User, Class, Trial, TrialQuestion, TrialQuestionProgress, StudentMistake
from app.models.learner_state import LearningEvent, LearnerState, LearnerStateChange, TutorDisplayReceipt
from app.services.learner_state import LearnerStateService as State
from app.services.assignment import AssignmentService
from app.services.mistake import MistakeService
from app.utils.time import utc_now


@pytest.fixture
def app(tmp_path, monkeypatch):
    schema = os.environ.get('PLEX_STATE_TEST_MYSQL_SCHEMA')
    if schema:
        import re
        assert re.fullmatch(r'plex_state_test_[a-f0-9]{12}', schema)
        url = make_url(DevelopmentConfig.SQLALCHEMY_DATABASE_URI).set(database=schema)
        uri = url.render_as_string(hide_password=False)
    else:
        uri = 'sqlite:///' + str(tmp_path / 'state.db')
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', uri)
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_ECHO', False)
    app = create_app('testing')
    with app.app_context():
        student = User.query.filter_by(username='student001').one()
        teacher = User.query.filter_by(username='teacher001').one()
        cls = Class(name='Evidence classroom', teacher_id=teacher.id, grade_level=1)
        db.session.add(cls); db.session.flush()
        student.class_id = cls.id
        # Deliberately already started: MySQL's legacy DATETIME(0) may round
        # an implicit utc_now() into the following second.
        trial = Trial(class_id=cls.id, teacher_id=teacher.id, title='可信判题', status='running',
                      starts_at=utc_now() - timedelta(minutes=1))
        db.session.add(trial); db.session.flush()
        q = TrialQuestion(trial_id=trial.id, stem='range(3) 的最后一个元素？', options=['2', '3'],
                          correct_index=0, knowledge_key='loop')
        db.session.add(q); db.session.flush()
        db.session.add(TrialQuestionProgress(user_id=student.id, question_id=q.id, status='pending'))
        db.session.commit()
        app.config['TEST_STUDENT'] = student.id
        app.config['TEST_TEACHER'] = teacher.id
        app.config['TEST_QUESTION'] = q.id
    yield app
    with app.app_context():
        db.session.remove()
        if schema:
            with db.engine.connect() as conn:
                conn.execute(text('SET FOREIGN_KEY_CHECKS=0'))
                for table in db.metadata.tables.values():
                    conn.execute(text('DROP TABLE IF EXISTS `' + table.name + '`'))
                conn.execute(text('SET FOREIGN_KEY_CHECKS=1'))
                conn.commit()
        db.engine.dispose()


def append(app, key='1', *, correct=True, assisted=False, when=None):
    return State.append(user_id=app.config['TEST_STUDENT'], kind='submission_graded',
        source_type='trial_question_progress', source_id=key, source_version='1', occurred_at=when,
        payload={'concept_id': 'loop', 'correct': correct, 'assisted': assisted, 'evidence_scope': 'server_graded'})


def snapshot(app):
    db.session.remove()
    return State.snapshot(app.config['TEST_STUDENT'])


def test_empty_is_unknown_not_zero(app):
    with app.app_context():
        assert snapshot(app)['concepts'] == []
        assert snapshot(app)['state_version'] == 0


def test_duplicate_and_rollback(app):
    with app.app_context():
        append(app); db.session.rollback()
        assert LearningEvent.query.count() == 0
        first = append(app); second = append(app)
        assert first.id == second.id
        db.session.commit()
        assert State.drain() == 1
        assert State.drain() == 0
        s = snapshot(app)
        assert s['state_version'] == 1
        assert s['concepts'][0]['independent_count'] == 1
        assert LearnerStateChange.query.count() == 1


def test_hundred_committed_retries_after_projection_change_state_once(app):
    """Plan section 11: repeated deliveries, including new DB sessions."""
    with app.app_context():
        first = append(app)
        event_id = first.id
        db.session.commit()
        assert State.drain() == 1
        for _ in range(100):
            # Each retry has its own transaction, after the first event was
            # already consumed. Identity-map reuse cannot satisfy this check.
            db.session.remove()
            retry = append(app)
            assert retry.id == event_id
            db.session.commit()
            assert State.drain() == 0
        s = snapshot(app)
        assert s['state_version'] == 1
        assert s['concepts'][0]['independent_count'] == 1
        assert LearningEvent.query.count() == LearnerStateChange.query.count() == 1


def test_assisted_and_independent_evidence_distinct(app):
    with app.app_context():
        append(app, '1'); append(app, '2', assisted=True); append(app, '3', correct=False)
        db.session.commit(); State.drain()
        c = snapshot(app)['concepts'][0]
        assert (c['independent_count'], c['independent_success'], c['assisted_count'], c['assisted_success']) == (2, 1, 1, 1)
        assert c['estimate'] == round(2.5 / 4.5, 4)


def test_hint_only_after_ack_and_owned(app):
    with app.app_context():
        uid = app.config['TEST_STUDENT']
        rid = State.issue_receipt(uid, text='检查结束位置', mode='next_step', concept_id='loop', question_id=app.config['TEST_QUESTION'])
        db.session.commit()
        assert LearningEvent.query.count() == 0
        with pytest.raises(LookupError):
            State.acknowledge_hint(app.config['TEST_TEACHER'], rid)
        State.acknowledge_hint(uid, rid); State.acknowledge_hint(uid, rid)
        State.drain()
        c = snapshot(app)['concepts'][0]
        assert c['hints_seen'] == 1 and c['estimate'] is None
        assert c['independent_count'] == 0


def test_lease_expiration_recovers_and_old_worker_cannot_commit(app):
    with app.app_context():
        append(app); db.session.commit()
        old = State.claim()
        assert State.claim() is None
        db.session.query(LearningEvent).update({'lease_until': utc_now() - timedelta(seconds=1)})
        db.session.commit()
        new = State.claim()
        assert old[0] == new[0] and old[1] != new[1]
        assert not State.process_claim(*old)
        assert State.process_claim(*new)
        assert not State.process_claim(*new)
        assert snapshot(app)['state_version'] == 1


def test_parallel_workers_no_lost_updates(app):
    with app.app_context():
        for n in range(20): append(app, str(n))
        db.session.commit()
    def consume(_):
        with app.app_context(): return State.drain(40)
    with ThreadPoolExecutor(max_workers=4) as pool:
        counts = list(pool.map(consume, range(4)))
    with app.app_context():
        assert sum(counts) == 20
        s = snapshot(app)
        assert s['state_version'] == 20
        assert s['concepts'][0]['independent_count'] == 20
        assert LearnerStateChange.query.count() == 20


def test_invalid_evidence_never_changes_state(app):
    with app.app_context():
        e = append(app)
        e.payload = {**e.payload, 'evidence_scope': 'client_tests'}
        db.session.commit()
        assert State.drain() == 0
        assert snapshot(app)['state_version'] == 0
        assert LearningEvent.query.one().status == 'failed'


@pytest.mark.parametrize('mutation', ['stale', 'extra_field', 'invented_evidence', 'override'])
def test_untrusted_proposals_rejected(app, mutation):
    with app.app_context():
        e = append(app); db.session.commit()
        state = LearnerState(user_id=app.config['TEST_STUDENT'], course='python', version=0, policy_version='evidence-heuristic-v1')
        db.session.add(state); db.session.commit()
        p = State.propose(e, state.version)
        if mutation == 'stale': p['base_version'] = -1
        elif mutation == 'extra_field': p['mastery'] = 1
        elif mutation == 'invented_evidence': p['evidence_ids'] = [9999]
        else: p['proposed_changes'] = {'estimate': 1}
        with pytest.raises(ValueError): State._commit_proposal(db.session, state, e, p)
        db.session.rollback()
        assert snapshot(app)['state_version'] == 0


def test_out_of_order_preserves_latest_evidence(app):
    with app.app_context():
        recent = utc_now()
        append(app, 'new', when=recent); db.session.commit(); State.drain()
        append(app, 'old', when=recent - timedelta(days=40)); db.session.commit(); State.drain()
        c = snapshot(app)['concepts'][0]
        assert c['last_evidence_at'] == recent.isoformat() and not c['stale']


def test_actual_formal_submission_is_atomic_with_event(app):
    with app.app_context(), patch('app.services.grading_orchestrator.GradingOrchestrator.run_after_submit', return_value=[]):
        uid, qid = app.config['TEST_STUDENT'], app.config['TEST_QUESTION']
        # Isolate legacy optional side effects; inspect the authoritative new transaction.
        with patch.object(AssignmentService, '_maybe_auto_complete_trial', return_value=None), \
             patch.object(AssignmentService, 'list_for_student', return_value={}), \
             patch('app.services.learning_adaptation.LearningAdaptationService.record_answer', return_value=None), \
             patch('app.services.daily_quest.DailyQuestService.advance_progress', return_value={}):
            result = AssignmentService.submit_answer(uid, qid, 0)
            assert result['correct']
            assert LearningEvent.query.one().payload['question_id'] == qid
            assert TrialQuestionProgress.query.one().status == 'completed'
            with pytest.raises(ValueError): AssignmentService.submit_answer(uid, qid, 0)
        State.drain()
        assert snapshot(app)['concepts'][0]['independent_success'] == 1


def test_failed_event_insert_rolls_back_grade(app):
    with app.app_context(), patch.object(State, 'record_submission', side_effect=RuntimeError('storage unavailable')):
        with pytest.raises(RuntimeError):
            AssignmentService.submit_answer(app.config['TEST_STUDENT'], app.config['TEST_QUESTION'], 0)
        db.session.rollback()
        assert TrialQuestionProgress.query.one().status == 'pending'
        assert LearningEvent.query.count() == 0


def test_client_test_log_cannot_create_mistake_or_evidence(app):
    with app.app_context():
        token = create_access_token(identity=str(app.config['TEST_STUDENT']))
    r = app.test_client().post('/api/v1/student/code-trial/runs',
        headers={'Authorization': 'Bearer ' + token}, json={'passed': True, 'knowledge_key': 'loop', 'question_id': 'x'})
    assert r.status_code == 200 and r.json['data']['evidence_scope'] == 'self_test'
    with app.app_context():
        assert LearningEvent.query.count() == 0 and StudentMistake.query.count() == 0


def test_read_endpoints_enforce_owner_and_class(app):
    with app.app_context():
        teacher = app.config['TEST_TEACHER']; student = app.config['TEST_STUDENT']
        tokens = {uid: create_access_token(identity=str(uid)) for uid in (teacher, student)}
    client = app.test_client()
    auth = lambda uid: {'Authorization': 'Bearer ' + tokens[uid]}
    assert client.get('/api/v1/student/learner-state').status_code == 401
    assert client.get('/api/v1/student/learner-state', headers=auth(teacher)).status_code == 403
    assert client.get(f'/api/v1/teacher/students/{student}/learner-state', headers=auth(teacher)).status_code == 200
    assert client.get(f'/api/v1/teacher/students/{student}/learner-state', headers=auth(student)).status_code == 403
    with app.app_context():
        db.session.get(User, student).class_id = None; db.session.commit()
    assert client.get(f'/api/v1/teacher/students/{student}/learner-state', headers=auth(teacher)).status_code == 403


def test_review_is_atomic_self_report_without_mastery(app):
    with app.app_context():
        uid = app.config['TEST_STUDENT']
        row = StudentMistake(user_id=uid, source='mcq', last_failed_at=utc_now(), question_ref='review-test',
            question_title='循环复习', knowledge_key='loop', fail_count=1, meta={})
        db.session.add(row); db.session.commit()
        mid = row.id
        with patch('app.services.student_profile.StudentProfileService.update_from_sm2_review', side_effect=RuntimeError('fail')):
            with pytest.raises(RuntimeError): MistakeService.submit_review(uid, mid, 5)
        db.session.rollback()
        assert LearningEvent.query.count() == 0
        assert not StudentMistake.query.one().meta.get('review_schedule')
        MistakeService.submit_review(uid, mid, 5)
        State.drain()
        c = snapshot(app)['concepts'][0]
        assert c['review_count'] == 1 and c['estimate'] is None
        assert c['review_due_at']


def test_due_scanner_is_idempotent(app):
    from app.services.learning_event_worker import scan_due_reviews
    with app.app_context():
        row = StudentMistake(user_id=app.config['TEST_STUDENT'], source='mcq', last_failed_at=utc_now(), question_ref='due-test',
            question_title='循环复习', knowledge_key='loop', fail_count=1,
            meta={'review_schedule': {'due_at': (utc_now() - timedelta(days=1)).isoformat() + 'Z'}})
        db.session.add(row); db.session.commit()
        scan_due_reviews(); scan_due_reviews(); State.drain()
        assert LearningEvent.query.count() == 1
        assert snapshot(app)['concepts'][0]['estimate'] is None


def test_migration_upgrade_repeat_and_downgrade(app):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261015_0018_learner_state.py'
    spec = importlib.util.spec_from_file_location('learner_migration', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    next_path = path.with_name('20261016_0019_learner_misconceptions.py')
    next_spec = importlib.util.spec_from_file_location('misconception_migration', next_path)
    next_module = importlib.util.module_from_spec(next_spec); next_spec.loader.exec_module(next_module)
    with app.app_context(), db.engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            next_module.downgrade()
            module.downgrade()
            module.upgrade(); module.upgrade()
            next_module.upgrade(); next_module.upgrade()
        tables = inspect(conn).get_table_names()
        assert 'learning_events' in tables and 'tutor_display_receipts' in tables
        assert 'learner_misconceptions' in tables and 'learner_misconception_evidence' in tables


def test_evidence_context_uses_one_source_and_preserves_unknown(app):
    from app.services.knowledge.learner_context_service import LearnerContextService
    from app.data.knowledge_node_registry import resolve_node_id
    with app.app_context():
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        with patch('app.services.knowledge_graph.KnowledgeGraphService.get_student_graph', side_effect=AssertionError('legacy read')):
            empty = LearnerContextService.build(app.config['TEST_STUDENT'])
            assert empty.state_version == 0 and empty.mastery == {}
            append(app); db.session.commit(); State.drain(); db.session.remove()
            ctx = LearnerContextService.build(app.config['TEST_STUDENT'])
            assert ctx.state_source == 'evidence' and ctx.state_version == 1
            assert ctx.mastery[resolve_node_id('loop')] == round(2/3, 4)


def test_help_receipt_only_after_response_and_class_validation(app):
    with app.app_context():
        uid, qid = app.config['TEST_STUDENT'], app.config['TEST_QUESTION']
        token = create_access_token(identity=str(uid))
    client = app.test_client(); headers = {'Authorization': 'Bearer ' + token}
    with patch('app.services.tutoring.TutorService.generate', return_value=({'summary':'检查边界', 'next_step':'列出边界。', 'follow_up':'', 'citations':[]}, None)) as coach, \
         patch('app.services.tutoring.KnowledgeService.tutor_evidence', return_value={'status':'insufficient_evidence','sources':[], 'prerequisite_gaps':[]}):
        denied = client.post('/api/v1/agents/trial-coach', headers=headers, json={'formalQuestionId': 987654})
        assert denied.status_code == 404 and not coach.called
        r = client.post('/api/v1/agents/trial-coach', headers=headers, json={'formalQuestionId': qid})
        assert r.status_code == 200
        rid = r.json['data']['display_receipt_id']
    with app.app_context():
        assert LearningEvent.query.count() == 0
    assert client.post(f'/api/v1/student/tutor-responses/{rid}/displayed', headers=headers).status_code == 200
    assert client.post(f'/api/v1/student/tutor-responses/{rid}/displayed', headers=headers).status_code == 200
    with app.app_context():
        assert LearningEvent.query.count() == 1


def test_concurrent_formal_submissions_create_one_grade_event(app):
    from threading import Barrier
    barrier = Barrier(2)
    def submit(_):
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                AssignmentService.submit_answer(app.config['TEST_STUDENT'], app.config['TEST_QUESTION'], 0)
                return 'graded'
            except ValueError as exc:
                assert str(exc) == '该题已完成'
                return 'already_graded'
    with patch('app.services.grading_orchestrator.GradingOrchestrator.run_after_submit', return_value=[]), \
         patch.object(AssignmentService, 'list_for_student', return_value={}), \
         patch.object(AssignmentService, '_maybe_auto_complete_trial', return_value=None), \
         patch('app.services.mistake.MistakeService.record_mcq_correct', return_value=None), \
         patch('app.services.learning_adaptation.LearningAdaptationService.record_answer', return_value=None), \
         patch('app.services.daily_quest.DailyQuestService.advance_progress', return_value={}):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
    assert sorted(results) == ['already_graded', 'graded']
    with app.app_context():
        assert LearningEvent.query.count() == 1
        assert State.drain() == 1
        assert snapshot(app)['concepts'][0]['independent_count'] == 1
