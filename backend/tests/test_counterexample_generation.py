"""Real transactions around fake provider/sandbox boundaries, not fake queue state."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch, Mock
import json
import pytest
from sqlalchemy import update
from test_counterexample_gates import (app, uid, auth, call, spec_body, proposed, fake_run,
    review, review_body, public)
from app.models import db, User
from app.models.counterexample import (CounterexampleGenerationTask as Task,
    CounterexampleGenerationCall as Call, CounterexampleChallenge as Challenge)
from app.services.counterexample_generation import (CounterexampleGenerationService as Tasks, run_once, claim, execute)
from app.services.counterexample_generation_model import CHECKS, generate
from app.services.knowledge.providers.llm import LLMResult, OpenAICompatibleLLMProvider
from app.services.execution_errors import ExecutionUnavailable
from app.utils.time import utc_now

ROOT = 'teacher/counterexample-generation-tasks'
REVIEW = {'verdict':'pass', 'checks':{key:True for key in CHECKS}, 'note':'单一循环边界错误，与执行差异一致。', 'quotes':[proposed()['explanation']]}


def make_task(app, request_id=None, spec_id=None):
    with app.app_context(): cohort = db.session.get(User, app.config['TEST_STUDENT']).class_id
    if not spec_id:
        basis = call(app, 'teacher/counterexample-specifications', {'request_id':uid(),'class_id':cohort,'specification':spec_body()})
        assert basis.status_code == 200, basis.json
        spec_id = basis.json['data']['id']
    response = call(app, ROOT, {'request_id':request_id or uid(), 'spec_id':spec_id, 'bug_kind':'loop_boundary'})
    assert response.status_code == 200, response.json
    return response.json['data']


def read(app, task):
    return app.test_client().get('/api/v1/'+ROOT+'/'+task['id'], headers=auth(app)).json['data']


def provider_result(value):
    return LLMResult(text=json.dumps(value, ensure_ascii=False), provider='fixture', model='contract-test', token_usage={'total_tokens':20})


@pytest.fixture
def boundaries(app):
    app.config['TUTOR_MODELS_ENABLED'] = True
    with patch('app.services.counterexample_generation_model.provider') as factory, patch(
            'app.services.counterexample_validation.CodeExecutionService.run', side_effect=fake_run) as sandbox:
        client = factory.return_value
        client.available.return_value = True
        client.generate.side_effect = [provider_result(proposed()), provider_result(REVIEW)]
        yield client, sandbox


def test_pipeline_binds_both_reviews_and_never_publishes(app, boundaries):
    task = make_task(app)
    assert run_once(app)
    done = read(app, task)
    assert done['status'] == 'ready' and done['attempts'] == 1
    assert len(done['calls']) == 2 and all(c['completed_at'] for c in done['calls'])
    assert done['pedagogy_review']['validation_id'] == done['validation_id']
    detail = app.test_client().get('/api/v1/teacher/counterexample-challenges/'+task['challenge_id'], headers=auth(app)).json['data']
    assert detail['origin'] == 'model_generated' and detail['generation']['status'] == 'ready'
    assert detail['published_revision'] is None and public(app,detail).status_code == 404
    assert review(app,detail,review_body(detail,done['validation_id'])).status_code == 200
    student = public(app, detail)
    assert student.status_code == 200 and 'candidate' not in student.json['data'] and 'generation' not in student.json['data']
    assert boundaries[1].call_count == 6
    # Generator gets a fixed teacher oracle, never an API to alter it.
    sent = json.loads(boundaries[0].generate.call_args_list[0].kwargs['user'])
    assert sent['specification']['tests'] == spec_body()['tests']


@pytest.mark.parametrize('bad', [
    {'buggy_code':'import os', **{k:v for k,v in proposed().items() if k!='buggy_code'}},
    {**proposed(), 'tests':[{'input':[], 'expected':9}]},
    {**proposed(), 'bug_kind':'empty_input'},
])
def test_model_cannot_edit_oracle_or_skip_static_gate(app, boundaries, bad):
    boundaries[0].generate.side_effect = [provider_result(bad)]
    task = make_task(app); run_once(app)
    done = read(app,task)
    assert done['status'] == 'rejected' and done['error_code'] == 'candidate_contract_rejected'
    assert not done['version_id'] and boundaries[1].call_count == 0
    with app.app_context(): assert Challenge.query.count() == 0


def test_rejected_execution_skips_teaching_model_and_cannot_publish(app, boundaries):
    boundaries[0].generate.side_effect = [provider_result({**proposed(), 'buggy_code':proposed()['fixed_code']})]
    task = make_task(app); run_once(app)
    done = read(app,task)
    assert done['status'] == 'rejected' and done['error_code'] == 'execution_rejected'
    assert boundaries[0].generate.call_count == 1


@pytest.mark.parametrize('audit', [
    {**REVIEW, 'quotes':['invented quote']},
    {**REVIEW, 'checks':{**REVIEW['checks'], 'single_clear_bug':False}},
    {**REVIEW, 'verdict':'uncertain'},
])
def test_invalid_or_uncertain_model_review_needs_revision_before_publication(app, boundaries, audit):
    boundaries[0].generate.side_effect = [provider_result(proposed()),provider_result(audit)]
    task=make_task(app); run_once(app); done=read(app,task)
    assert done['status'] == 'rejected'
    detail=app.test_client().get('/api/v1/teacher/counterexample-challenges/'+task['challenge_id'],headers=auth(app)).json['data']
    assert detail['validation']['status']=='passed'
    assert review(app,detail,review_body(detail,done['validation_id'])).status_code==409


def test_idempotent_creation_quota_and_role_ownership(app):
    app.config['COUNTEREXAMPLE_GENERATION_DAILY_LIMIT']=1
    task=make_task(app)
    assert make_task(app,task['id'],task['spec_id'])['id']==task['id']
    response=call(app,ROOT,{'request_id':uid(),'spec_id':task['spec_id'],'bug_kind':'loop_boundary'})
    assert response.status_code==429
    assert call(app,ROOT,{'request_id':task['id'],'spec_id':task['spec_id'],'bug_kind':'empty_input'}).status_code==409
    for verb in ('get','post'):
        path='/api/v1/'+ROOT+'/'+task['id']+('/cancel' if verb=='post' else '')
        assert getattr(app.test_client(),verb)(path,headers=auth(app,'student')).status_code==403
    cancelled=call(app,ROOT+'/'+task['id']+'/cancel',{}).json['data']
    assert cancelled['status']=='cancelled' and not run_once(app)
    # Cancelling never refunds creation quota or resurrects the same ID.
    assert make_task(app,task['id'],task['spec_id'])['status']=='cancelled'
    assert call(app,ROOT+'/'+task['id']+'/retry',{'expected_attempts':0}).status_code==409


def test_atomic_concurrent_quota_and_same_request(app):
    app.config['COUNTEREXAMPLE_GENERATION_ACTIVE_LIMIT']=1
    first=make_task(app)
    call(app,ROOT+'/'+first['id']+'/cancel',{})
    def create(request_id):
        with app.app_context():
            try:
                return Tasks.create(app.config['TEST_TEACHER'], {'request_id':request_id,'spec_id':first['spec_id'],'bug_kind':'loop_boundary'})['id']
            except Exception as exc:
                return getattr(exc,'status',str(type(exc)))
            finally: db.session.remove()
    shared=uid()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(create,[shared,shared,uid()]))
    # Exactly one new task can enter the queue; duplicates of the winner are harmless.
    with app.app_context(): assert Task.query.filter_by(status='queued').count()==1
    assert all(item in {shared,429} or isinstance(item,str) and len(item)==36 for item in results), results


def test_cancel_during_model_retains_call_audit_but_no_candidate(app, boundaries):
    entered, release=Event(),Event()
    def delayed(**kwargs):
        entered.set(); assert release.wait(15); return provider_result(proposed())
    boundaries[0].generate.side_effect=delayed
    task=make_task(app)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(run_once,app)
        assert entered.wait(10)
        assert call(app,ROOT+'/'+task['id']+'/cancel',{}).json['data']['status']=='cancelled'
        release.set(); future.result(timeout=15)
    done=read(app,task)
    assert done['status']=='cancelled' and not done['version_id']
    assert len(done['calls'])==1 and done['calls'][0]['audit']['token_usage']['total_tokens']==20
    assert boundaries[1].call_count==0


def test_retry_resumes_saved_candidate_without_new_generation(app, boundaries):
    task=make_task(app)
    boundaries[1].side_effect=ExecutionUnavailable()
    run_once(app); failed=read(app,task)
    assert failed['status']=='failed' and failed['stage']=='validation' and failed['retryable']
    assert boundaries[0].generate.call_count==1
    response=call(app,ROOT+'/'+task['id']+'/retry',{'expected_attempts':1})
    assert response.status_code==200 and response.json['data']['status']=='queued'
    boundaries[1].side_effect=fake_run
    run_once(app); done=read(app,task)
    assert done['status']=='ready' and done['attempts']==2 and boundaries[0].generate.call_count==2
    assert done['version_id']==failed['version_id'] and done['validation_id']==failed['validation_id']
    assert call(app,ROOT+'/'+task['id']+'/retry',{'expected_attempts':1}).json['data']['status']=='ready'


def test_cancel_during_execution_keeps_report_but_never_advances_review_or_publish(app, boundaries):
    task=make_task(app)
    entered,release=Event(),Event()
    def held(*args):
        if not entered.is_set():
            entered.set(); assert release.wait(15)
        return fake_run(*args)
    boundaries[1].side_effect=held
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(run_once,app); assert entered.wait(10)
        assert call(app,ROOT+'/'+task['id']+'/cancel',{}).json['data']['status']=='cancelled'
        release.set(); future.result(timeout=15)
    done=read(app,task)
    assert done['status']=='cancelled' and boundaries[0].generate.call_count==1
    detail=app.test_client().get('/api/v1/teacher/counterexample-challenges/'+task['challenge_id'],headers=auth(app)).json['data']
    assert detail['validation']['status']=='passed'
    assert review(app,detail,review_body(detail,done['validation_id'])).status_code==409


def test_teaching_outage_retries_only_review_and_recovery_is_bounded(app, boundaries):
    task=make_task(app)
    boundaries[0].generate.side_effect=[provider_result(proposed()),None,provider_result(REVIEW)]
    run_once(app); failed=read(app,task)
    assert failed['status']=='failed' and failed['stage']=='pedagogy'
    assert call(app,ROOT+'/'+task['id']+'/retry',{'expected_attempts':1}).status_code==200
    run_once(app)
    assert read(app,task)['status']=='ready' and boundaries[1].call_count==6
    next_task=make_task(app)
    boundaries[0].generate.side_effect=None;boundaries[0].generate.return_value=None
    for expected in (1,2,3):
        run_once(app); failed=read(app,next_task)
        assert failed['status']=='failed' and failed['attempts']==expected
        if expected<3:
            assert call(app,ROOT+'/'+next_task['id']+'/retry',{'expected_attempts':expected}).status_code==200
    assert not failed['retryable'] and not run_once(app)


def test_expired_claim_is_fenced_and_recovered(app, boundaries):
    task=make_task(app)
    with app.app_context():
        first=claim(); assert first
        db.session.execute(update(Task).where(Task.id==task['id']).values(lease_until=utc_now()-timedelta(seconds=1)))
        db.session.commit()
        second=claim(); assert second and second[1]!=first[1]
        execute(*first)
        assert boundaries[0].generate.call_count==0
        execute(*second)
    assert read(app,task)['status']=='ready'


def test_permission_revoked_during_generation_cannot_create_version(app, boundaries):
    def revoke(**kwargs):
        with app.app_context():
            user=db.session.get(User,app.config['TEST_TEACHER']);user.status='frozen';db.session.commit()
        return provider_result(proposed())
    boundaries[0].generate.side_effect=revoke
    task=make_task(app);run_once(app)
    with app.app_context():
        row=db.session.get(Task,task['id'])
        assert row.status=='failed' and row.error_code=='permission_changed' and row.version_id is None
        assert Call.query.count()==1


def test_structured_provider_preserves_multiplication_and_duplicate_fields_fail(app):
    raw=json.dumps({**proposed(), 'fixed_code':'def solve(data):\n    return data * 2 * 3'})
    response=Mock();response.json.return_value={'choices':[{'message':{'content':raw}}]}
    with app.app_context(), patch.object(OpenAICompatibleLLMProvider,'_resolve',return_value=('fixture','https://example.test','fixture')),patch(
            'app.services.knowledge.providers.llm.direct_post',return_value=response):
        assert OpenAICompatibleLLMProvider('structured_code').generate(system='x',user='y').text==raw
    app.config['TUTOR_MODELS_ENABLED']=True
    with app.app_context(),patch('app.services.counterexample_generation_model.provider') as factory:
        factory.return_value.generate.return_value=LLMResult(text='{"bug_kind":"loop_boundary","bug_kind":"empty_input"}')
        proposal,audit=generate(spec_body(),'loop_boundary')
        assert proposal is None and audit['error_code']=='candidate_contract_rejected'
