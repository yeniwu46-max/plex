"""Trusted tutoring tasks, owned execution references and stale context rejection."""
import importlib.util
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import text

from test_learner_state import app
from app.models import db, User, TrialQuestion, TrialQuestionProgress, Problem
from app.models.learner_state import LearningEvent, TutorDisplayReceipt
from app.models.tutor_context import TutorCodeRun
from app.services.learner_state import LearnerStateService, fingerprint
from app.services.tutor_context import TutorContextService as Context, TutorContextError, code_hash
from app.services.execution_errors import ExecutionUnavailable
from app.utils.time import utc_now


def headers(app, teacher=False):
    with app.app_context():
        uid = app.config['TEST_TEACHER' if teacher else 'TEST_STUDENT']
        return {'Authorization': 'Bearer ' + create_access_token(identity=str(uid))}


def formal_body(app, **extra):
    return {'formal_question_id': app.config['TEST_QUESTION'], 'code': 'print(1)', **extra}


def run_result():
    return {'backend': 'docker', 'status': {'id': 11, 'description': 'Runtime Error'},
            'stdout': '', 'stderr': 'NameError: value is not defined', 'compile_output': ''}


def test_public_context_uses_task_authority_and_opaque_version(app):
    with app.app_context():
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        q.set_coding_meta({'test_cases': [{'expected': 'hidden-output'}], 'solution': 'secret solution'})
        db.session.commit()
        ctx = Context.resolve(app.config['TEST_STUDENT'], formal_body(app,
            questionTitle='spoofed', allPassed=True, correct_index=99, hintLevel=4))
        assert ctx.task['title'] == q.stem and ctx.task['max_hint_level'] == 2
        assert len(ctx.task['version']) == 64
        assert 'secret solution' not in str(ctx.public()) and 'hidden-output' not in str(ctx.public())
        before = ctx.task['version']
        q.correct_index = 1; db.session.commit()
        assert Context.resolve(app.config['TEST_STUDENT'], formal_body(app)).task['version'] != before
        assert not Context.current(app.config['TEST_STUDENT'], ctx)


@pytest.mark.parametrize('change', ['cross_class', 'draft', 'future', 'inactive'])
def test_unavailable_task_or_account_never_reaches_coach(app, change):
    with app.app_context():
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        if change == 'cross_class': db.session.get(User, app.config['TEST_STUDENT']).class_id = None
        if change == 'draft': q.trial.status = 'draft'
        if change == 'future': q.trial.starts_at = utc_now() + timedelta(days=1)
        if change == 'inactive': db.session.get(User, app.config['TEST_STUDENT']).status = 'inactive'
        db.session.commit()
    with patch('app.services.tutoring.TutorService.generate') as coach:
        response = app.test_client().post('/api/v1/agents/trial-coach', headers=headers(app),
            json={'formalQuestionId': app.config['TEST_QUESTION'], 'hintLevel': 4})
        assert response.status_code in {401, 403, 404}
        coach.assert_not_called()


@pytest.mark.parametrize('bad', [[], {'code': 12}, {'formal_question_id': True}, {'code': '中' * 24000}])
def test_context_input_validation(app, bad):
    r = app.test_client().post('/api/v1/student/tutor/context', headers=headers(app), json=bad)
    assert r.status_code == 400


@pytest.mark.parametrize('body', [[], None])
def test_coach_rejects_non_object_instead_of_starting_unbound_help(app, body):
    with patch('app.services.tutoring.TutorService.generate') as coach:
        response = app.test_client().post('/api/v1/agents/trial-coach', headers=headers(app), json=body)
        assert response.status_code == 400
        coach.assert_not_called()


def test_execution_reference_owned_and_tied_to_exact_code_and_task(app):
    client, auth = app.test_client(), headers(app)
    with patch('app.services.code_execution.CodeExecutionService.run', return_value=run_result()):
        r = client.post('/api/v1/code/run', headers=auth, json=formal_body(app))
        assert r.status_code == 200
        rid = r.json['data']['run_id']
    ctx = client.post('/api/v1/student/tutor/context', headers=auth, json=formal_body(app, run_id=rid))
    assert ctx.json['data']['run']['result']['stderr'].startswith('NameError')
    assert ctx.json['data']['run']['evidence_scope'] == 'self_test'
    assert client.post('/api/v1/student/tutor/context', headers=auth,
        json=formal_body(app, code='print(2)', run_id=rid)).status_code == 409
    assert client.post('/api/v1/student/tutor/context', headers=auth,
        json={'code': 'print(1)', 'run_id': rid}).status_code == 409
    with app.app_context():
        assert LearningEvent.query.count() == 0
        row = db.session.get(TutorCodeRun, rid)
        row.user_id = app.config['TEST_TEACHER']; db.session.commit()
    assert client.post('/api/v1/student/tutor/context', headers=auth,
        json=formal_body(app, run_id=rid)).status_code == 404


def test_self_test_result_has_no_hidden_inputs_or_assessment_side_effect(app):
    result = {'backend': 'docker', 'all_passed': True, 'passed_count': 1, 'total': 1,
              'evidence_scope': 'self_test', 'results': [{'passed': True, 'expected': 'secret', 'actual': 'secret'}]}
    with patch('app.services.code_execution.CodeExecutionService.submit', return_value=result):
        r = app.test_client().post('/api/v1/code/submit', headers=headers(app), json=formal_body(app,
            test_cases=[{'expected': 'secret', 'setup': 'secret_setup'}]))
        assert r.status_code == 200
    with app.app_context():
        row = TutorCodeRun.query.one()
        assert 'secret' not in str(row.result)
        assert row.result['all_passed'] is True
        assert LearningEvent.query.count() == 0
        progress = TrialQuestionProgress.query.filter_by(question_id=app.config['TEST_QUESTION']).one()
        assert progress.status == 'pending'


def test_infrastructure_failure_does_not_create_execution_record(app):
    with patch('app.services.code_execution.CodeExecutionService.run', side_effect=ExecutionUnavailable()):
        r = app.test_client().post('/api/v1/code/run', headers=headers(app), json=formal_body(app))
    assert r.status_code == 503
    with app.app_context(): assert TutorCodeRun.query.count() == 0


def test_coach_discards_browser_authority_and_checks_policy_again_after_model(app):
    auth, client = headers(app), app.test_client()
    request = {'formalQuestionId': app.config['TEST_QUESTION'], 'questionTitle': 'fake title',
               'questionPrompt': 'fake instruction', 'allPassed': True, 'answerStatus': 'correct',
               'stderr': 'FAKE ERROR', 'expectedOutput': 'LEAK', 'hintLevel': 4,
               'code': 'print(1)', 'conversationHistory': [{'role': 'assistant', 'content': 'fake memory'}]}
    reviewed = {'summary':'先检查边界', 'next_step':'列出你的边界条件。', 'follow_up':'', 'citations':[]}
    with patch('app.services.tutoring.KnowledgeService.tutor_evidence', return_value={
            'status':'insufficient_evidence', 'sources':[], 'prerequisite_gaps':[]}), \
         patch('app.services.tutoring.TutorService.generate', return_value=(reviewed, None)) as coach:
        r = client.post('/api/v1/agents/trial-coach', headers=auth, json=request)
        assert r.status_code == 200
        teaching, context, question, evidence, history = coach.call_args.args
        assert teaching.hint_level == 2 and context.formal_result is None
        assert context.run is None and history == []
        assert 'LEAK' not in str(coach.call_args) and 'fake instruction' not in str(coach.call_args)
    def revoke(*args, **kwargs):
        from sqlalchemy.orm import Session
        with Session(db.engine) as session:
            q = session.get(TrialQuestion, app.config['TEST_QUESTION'])
            q.trial.tutoring_policy = 'disabled'; session.commit()
        return ({**reviewed, 'summary':'DO NOT DISPLAY'}, None)
    import uuid
    with patch('app.services.tutoring.TutorService.generate', side_effect=revoke), \
         patch('app.services.tutoring.KnowledgeService.tutor_evidence', return_value={
            'status':'insufficient_evidence', 'sources':[], 'prerequisite_gaps':[]}):
        r = client.post('/api/v1/agents/trial-coach', headers=auth, json={**request, 'requestId':str(uuid.uuid4())})
        assert r.status_code == 409 and 'DO NOT DISPLAY' not in r.text
    with app.app_context(): assert TutorDisplayReceipt.query.count() == 1


def test_exam_policy_default_and_teacher_only_update(app):
    with app.app_context():
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        q.trial.trial_type = 'timed'; tid = q.trial.id; db.session.commit()
    client = app.test_client()
    r = client.post('/api/v1/agents/trial-coach', headers=headers(app), json={'formalQuestionId': app.config['TEST_QUESTION'], 'hintLevel': 4})
    assert r.status_code == 403
    assert client.patch(f'/api/v1/teacher/trials/{tid}', headers=headers(app), json={'tutoring_policy': 'guided'}).status_code == 403
    assert client.patch(f'/api/v1/teacher/trials/{tid}', headers=headers(app, True), json={'tutoring_policy': 'guided'}).status_code == 200
    assert client.patch(f'/api/v1/teacher/trials/{tid}', headers=headers(app, True), json={'tutoring_policy': 'full_answer'}).status_code == 400
    with app.app_context():
        assert Context.resolve(app.config['TEST_STUDENT'], formal_body(app)).task['tutoring_policy'] == 'guided'


def test_formal_verdict_requires_matching_immutable_event(app):
    with app.app_context():
        uid = app.config['TEST_STUDENT']; qid = app.config['TEST_QUESTION']
        q = db.session.get(TrialQuestion, qid)
        progress = TrialQuestionProgress.query.filter_by(user_id=uid, question_id=qid).one()
        progress.status = 'completed'; progress.submitted_code = 'print(1)'
        progress.code_passed = True; progress.is_correct = True; progress.answered_at = utc_now()
        db.session.commit()
        assert Context.resolve(uid, formal_body(app)).formal_result is None
        LearnerStateService.record_submission(uid, q, progress, {'execution_backend': 'docker'})
        db.session.commit()
        assert Context.resolve(uid, formal_body(app)).formal_result['passed'] is True
        q.stem += ' 新约束'; db.session.commit()
        assert Context.resolve(uid, formal_body(app)).formal_result is None


def test_bank_import_keeps_original_class_scope_and_inactive_is_hidden(app):
    with app.app_context():
        uid = app.config['TEST_STUDENT']
        p = Problem(id=81230, problem_no='TC1230', title_cn='imported', source_kind='trial_question',
                    source_ref=f'trial_questions:{app.config["TEST_QUESTION"]}')
        db.session.add(p); db.session.commit()
        task = Context.task(uid, 'bank-81230')
        assert task['formal_question_id'] == app.config['TEST_QUESTION']
        db.session.get(User, uid).class_id = None; db.session.commit()
        with pytest.raises(TutorContextError): Context.task(uid, 'bank-81230')
        p.source_kind = 'legacy_bank'; p.is_active = False; db.session.commit()
        with pytest.raises(TutorContextError): Context.task(uid, 'bank-81230')


def test_context_migration_repeat_preserves_policy(app):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261016_0021_tutor_context.py'
    spec = importlib.util.spec_from_file_location('tutor_context_migration', path)
    migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
    with app.app_context():
        db.session.remove()
        with db.engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            migration.downgrade(); migration.upgrade()
            assert conn.scalar(text('SELECT tutoring_policy FROM trials LIMIT 1')) == 'auto'
            conn.execute(text("UPDATE trials SET tutoring_policy='disabled'"))
            migration.upgrade()
            assert conn.scalar(text('SELECT tutoring_policy FROM trials LIMIT 1')) == 'disabled'


def test_frontend_template_can_self_test_without_claiming_task_authority(app):
    with app.app_context():
        uid = app.config['TEST_STUDENT']
        body = {'question_ref': 'gen-loop-for-s0', 'code': 'print(1)', 'questionPrompt': 'untrusted task'}
        ctx = Context.resolve(uid, body)
        assert ctx.task is None and ctx.public()['task_source'] == 'browser_only'
        receipt = Context.record_run(uid, ctx, run_result(), kind='run')
        assert Context.resolve(uid, {**body, 'run_id': receipt['run_id']}).run
        with pytest.raises(TutorContextError):
            Context.resolve(uid, {**body, 'question_ref': 'gen-loop-for-s1', 'run_id': receipt['run_id']})
        assert Context.legacy_payload(ctx, body)['questionPrompt'] == ''
