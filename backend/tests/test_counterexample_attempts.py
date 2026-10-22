"""Student evidence is an owned, immutable execution fact, not a model grade."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
from threading import Event
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect
import pytest

from test_learner_state import app
from test_counterexample_gates import (make_challenge, call, auth, review, review_body,
    validate_body, validation_path, PASSED, fake_run, uid, proposed, spec_body)
from app.models import db, User
from app.models.counterexample import CounterexampleAttempt as Attempt, CounterexampleVersion as Version, CounterexampleExplanationReview
from app.models.learner_state import LearningEvent
from app.services.counterexample_contract import digest
from app.services.counterexample_validation import HARNESS
from app.services.counterexample_explanation import evaluate_explanation
from app.services.knowledge.providers.llm import LLMResult
from app.services.execution_errors import ExecutionUnavailable
from app.services.learner_state import LearnerStateService as State
from app.services.learner_decision import LearnerDecisionService
from app.utils.time import utc_now

RUNTIME = {'backend':'docker','python':'3.12.10','image_id':'sha256:verified-test-image','harness_hash':digest(HARNESS)}
EXPLANATION = '错误版遗漏最后一个元素，所以 [2,3] 的结果是 2 而不是 5。'


def publish(app):
    row=make_challenge(app);body=validate_body(row)
    with patch('app.services.counterexample.validate',return_value={**PASSED,'runtimes':[{'program':'reference',**RUNTIME}]}):
        assert call(app,validation_path(row),body).status_code==200
    assert review(app,row,review_body(row,body['request_id'])).status_code==200
    return row


def body_for(row,**extra):
    return {'request_id':uid(),'revision':row['current_revision'],'version':row['manifest_hash'],
        'input':[2,3],'expected_output':5,'explanation':EXPLANATION,**extra}


def submit(app,row,body):
    return call(app,'student/counterexample-challenges/'+row['id']+'/attempts',body,'student')


def read(app,body,kind='student'):
    return app.test_client().get('/api/v1/'+kind+'/counterexample-attempts/'+body['request_id'],headers=auth(app,kind))


class Provider:
    def __init__(self,raw=None):
        self.calls=[]
        self.raw=raw or {'verdict':'supported','reason':'adequate','checks':{
            'cause_explained':True,'connects_input_and_difference':True,'consistent_with_results':True},
            'quotes':['错误版遗漏最后一个元素']}
    def available(self): return True
    def generate(self,**kwargs):
        self.calls.append(kwargs)
        return LLMResult(text=json.dumps(self.raw),provider='test-provider',model='test-model',token_usage={'total_tokens':123})


def test_actual_facts_retry_restore_and_separate_learning_evidence(app):
    row=publish(app);body=body_for(row);provider=Provider()
    app.config['TUTOR_MODELS_ENABLED']=True
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run) as runner, \
         patch('app.services.counterexample_explanation.get_llm_provider',return_value=provider):
        response=submit(app,row,body);assert response.status_code==200,response.json
        data=response.json['data']
        assert data['counterexample_found'] and data['expected_output_correct'] and data['graded']
        assert data['correct_result']=={'kind':'value','value':5} and data['buggy_result']=={'kind':'value','value':2}
        assert data['explanation_review']['status']=='supported'
        assert submit(app,row,body).json['data']==data and read(app,body).json['data']==data
        history=app.test_client().get('/api/v1/student/counterexample-challenges/'+row['id']+'/attempts',headers=auth(app,'student'))
        assert history.status_code==200 and history.json['data']['items']==[
            {'request_id':body['request_id'],'status':'complete','created_at':data['created_at']}]
        assert runner.call_count==6 and len(provider.calls)==1
        assert submit(app,row,{**body,'input':[1,2]}).status_code==409
    sent=json.loads(provider.calls[0]['user'])
    assert set(sent)=={'statement','buggy_code','input','execution_facts','student_explanation'}
    assert 'fixed_code' not in str(sent) and 'tests' not in sent and 'reference_code' not in sent
    assert 'execution_report' not in data and 'token_usage' not in data['explanation_review']
    with app.app_context():
        assert Attempt.query.count()==LearningEvent.query.count()==1
        assert State.drain()==1 and State.drain()==0
        snapshot=State.snapshot(app.config['TEST_STUDENT']);concept=snapshot['concepts'][0]
        assert snapshot['state_version']==1 and concept['estimate'] is None
        assert concept['independent_count']==concept['assisted_count']==0
        assert concept['counterexample_count']==concept['counterexample_success']==1
        assert concept['counterexample_review_due_at']
        decision=LearnerDecisionService.from_snapshot(snapshot,now=utc_now()+timedelta(days=2))
        assert decision['basis']=='counterexample_review'


@pytest.mark.parametrize('input_value,expected,found,output_correct', [([],0,False,True),([2,3],4,True,False)])
def test_execution_dimensions_are_separate_and_model_not_called_without_valid_counterexample(app,input_value,expected,found,output_correct):
    row=publish(app);body=body_for(row,input=input_value,expected_output=expected)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run), \
         patch('app.services.counterexample_explanation.get_llm_provider') as provider:
        response=submit(app,row,body);assert response.status_code==200,response.json
    data=response.json['data']
    assert data['counterexample_found'] is found and data['expected_output_correct'] is output_correct
    assert data['explanation_review']['status']=='not_evaluated' and not provider.called
    with app.app_context():
        State.drain();concept=State.snapshot(app.config['TEST_STUDENT'])['concepts'][0]
        assert concept['counterexample_count']==1 and concept['counterexample_success']==0 and concept['estimate'] is None


def test_invalid_or_foreign_context_never_executes_or_counts(app):
    row=publish(app)
    with patch('app.services.counterexample_validation.CodeExecutionService.run') as runner:
        for body in ([],None,body_for(row,input=[True]),body_for(row,input=[999]),body_for(row,expected_output=False),
                     body_for(row,explanation=''),body_for(row,code='print(5)'),body_for(row,reference_code='spoof')):
            assert submit(app,row,body).status_code==400
        assert submit(app,row,body_for(row,revision=2)).status_code==409
        with app.app_context():
            db.session.get(User,app.config['TEST_STUDENT']).class_id=None;db.session.commit()
        assert submit(app,row,body_for(row)).status_code==404
        assert not runner.called
    with app.app_context(): assert Attempt.query.count()==LearningEvent.query.count()==0


def test_infrastructure_failure_retries_without_duplicate_evidence(app):
    row=publish(app);body=body_for(row)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=ExecutionUnavailable('busy')):
        response=submit(app,row,body)
    assert response.status_code==503 and not response.json['data']['graded']
    assert read(app,body).json['data']['retryable']
    with app.app_context(): assert LearningEvent.query.count()==0 and Attempt.query.one().status=='unavailable'
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run):
        assert submit(app,row,body).status_code==200
    with app.app_context(): assert LearningEvent.query.count()==1 and Attempt.query.count()==1


def test_new_input_exposes_material_problem_blocks_republication_and_never_grades_student(app):
    row=publish(app);body=body_for(row);count=0
    def inconsistent(*args):
        nonlocal count
        count+=1;result=fake_run(*args)
        if count in (3,4):
            parsed=json.loads(result['stdout']);parsed['results'][0]['value']=4;result['stdout']=json.dumps(parsed)
        return result
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=inconsistent):
        response=submit(app,row,body)
    assert response.status_code==200,response.json
    assert response.json['data']['status']=='material_issue' and not response.json['data']['graded']
    assert 'correct_result' not in response.json['data']
    with app.app_context():
        assert LearningEvent.query.count()==0
        version=Version.query.one();assert version.blocked_reason=='reference_fixed_disagreement'
    assert read(app,body).json['data']['status']=='material_issue'
    assert call(app,validation_path(row),validate_body(row)).status_code==409
    report=call(app,'teacher/counterexample-challenges/'+row['id']+'/review',
        {'action':'publish','manifest_hash':row['manifest_hash'],'validation_id':uid(),'note':'override','checks':{}},'admin')
    assert report.status_code==409
    assert read(app,body,'teacher').json['data']['execution_report']['material_issue']=='reference_fixed_disagreement'
    copied=call(app,'teacher/counterexample-challenges/'+row['id']+'/versions',
        {'request_id':uid(),'expected_revision':1,'spec_id':row['spec_id'],'candidate':proposed()})
    assert copied.status_code==400  # Must add this still-legal input to the independent regression suite.
    revised_spec=spec_body()
    revised_spec['tests'].append({'input':body['input'],'expected':body['expected_output']})
    specification=call(app,'teacher/counterexample-specifications',{'request_id':uid(),
        'class_id':row['class_id'],'specification':revised_spec})
    assert specification.status_code==200,specification.json
    repaired=call(app,'teacher/counterexample-challenges/'+row['id']+'/versions',
        {'request_id':uid(),'expected_revision':1,'spec_id':specification.json['data']['id'],'candidate':proposed()})
    assert repaired.status_code==200 and repaired.json['data']['current_revision']==2
    assert repaired.json['data']['published_revision'] is None


def test_attempt_history_and_read_are_private_even_within_same_class(app):
    row=publish(app);body=body_for(row)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run):
        assert submit(app,row,body).status_code==200
    with app.app_context():
        original=db.session.get(User,app.config['TEST_STUDENT'])
        other=User(username='counterexample_peer',email='counterexample-peer@example.com',password_hash='unused-test-hash',
            role_id=original.role_id,class_id=original.class_id,status='active')
        db.session.add(other);db.session.commit();app.config['TEST_STUDENT']=other.id
    history=app.test_client().get('/api/v1/student/counterexample-challenges/'+row['id']+'/attempts',headers=auth(app,'student'))
    assert history.status_code==200 and history.json['data']['items']==[]
    assert read(app,body).status_code==404


def test_teacher_withdrawal_during_execution_suppresses_result_and_event(app):
    row=publish(app);body=body_for(row);count=0
    def withdraw(*args):
        nonlocal count
        count+=1
        if count==1:
            assert review(app,row,{'action':'withdraw','manifest_hash':row['manifest_hash']}).status_code==200
        return fake_run(*args)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=withdraw):
        response=submit(app,row,body)
    assert response.status_code==409
    with app.app_context(): assert LearningEvent.query.count()==0 and Attempt.query.one().status=='stale'


def test_concurrent_same_request_has_one_execution(app):
    row=publish(app);body=body_for(row);entered,release=Event(),Event();calls=0
    def slow(*args):
        nonlocal calls
        calls+=1
        if calls==1: entered.set();assert release.wait(10)
        return fake_run(*args)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=slow),ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(submit,app,row,body)
        try:
            assert entered.wait(10)
            assert submit(app,row,body).status_code==409
            assert read(app,body).json['data']['status']=='processing'
        finally: release.set()
        assert future.result(timeout=15).status_code==200
    assert calls==6
    with app.app_context(): assert LearningEvent.query.count()==1


def test_expired_attempt_worker_cannot_replace_recovered_facts(app):
    row=publish(app);body=body_for(row)
    def expired(*args):
        record=db.session.get(Attempt,body['request_id'])
        record.lease_until=utc_now()-timedelta(seconds=1);db.session.commit()
        with patch('app.services.counterexample_attempt.probe') as probe:
            probe.return_value=({'counterexample_found':True,'expected_output_correct':True,
                'correct_result':{'kind':'value','value':5},'buggy_result':{'kind':'value','value':2}}, {'elapsed_ms':10})
            recovered=submit(app,row,body)
        assert recovered.status_code==200,recovered.json
        return None,{'material_issue':'old_worker_must_not_win','elapsed_ms':100}
    with patch('app.services.counterexample_attempt.probe',side_effect=expired):
        response=submit(app,row,body)
    assert response.status_code==409
    restored=read(app,body).json['data']
    assert restored['status']=='complete' and restored['counterexample_found']
    with app.app_context():
        assert LearningEvent.query.count()==1 and Version.query.one().blocked_reason is None


def test_runtime_changed_is_retryable_infrastructure_failure(app):
    row=publish(app);body=body_for(row)
    with patch('app.services.counterexample_attempt.run_function',return_value=(
            [{'kind':'value','value':5}],{**RUNTIME,'image_id':'sha256:new-image'})):
        assert submit(app,row,body).status_code==503
    with app.app_context():
        assert LearningEvent.query.count()==0 and Version.query.one().blocked_reason is None
    restored=read(app,body).json['data']
    assert restored['status']=='unavailable' and restored['retryable']


def test_transfer_reminder_does_not_return_when_late_practice_event_arrives(app):
    row=publish(app);body=body_for(row)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run):
        assert submit(app,row,body).status_code==200
    with app.app_context():
        practice=LearningEvent.query.one()
        formal=State.append(user_id=app.config['TEST_STUDENT'],kind='submission_graded',
            source_type='trial_question_progress',source_id='newer',source_version='1',
            occurred_at=utc_now()+timedelta(days=1),payload={'concept_id':practice.payload['concept_id'],
                'correct':True,'assisted':False,'evidence_scope':'server_graded'})
        db.session.commit()
        first,second=State.claim(),State.claim()
        assert first[0]==practice.id and second[0]==formal.id
        assert State.process_claim(*second)
        assert State.process_claim(*first)
        concept=State.snapshot(app.config['TEST_STUDENT'])['concepts'][0]
        assert concept['counterexample_review_due_at'] is None and concept['independent_count']==1


def test_teacher_explanation_correction_is_owned_idempotent_and_does_not_regrade(app):
    row=publish(app);body=body_for(row)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run):
        first=submit(app,row,body).json['data']
    assert first['explanation_review']['status']=='needs_teacher'
    review_request={'request_id':uid(),'expected_revision':0,'verdict':'needs_revision','note':'请明确指出切片为何遗漏最后一个元素。'}
    path='teacher/counterexample-attempts/'+body['request_id']+'/review'
    assert call(app,path,review_request,'student').status_code==403
    changed=call(app,path,review_request);assert changed.status_code==200,changed.json
    assert call(app,path,review_request).json==changed.json
    assert call(app,path,{**review_request,'request_id':uid()}).status_code==409
    now=read(app,body).json['data']
    assert now['explanation_review']['source']=='teacher' and now['explanation_review']['revision']==1
    for key in ('counterexample_found','expected_output_correct','correct_result','buggy_result','evidence_event_id'):
        assert now[key]==first[key]
    with app.app_context():
        assert LearningEvent.query.count()==1 and CounterexampleExplanationReview.query.count()==1
        assert Attempt.query.one().execution_report['initial_explanation_review']['status']=='needs_teacher'
    with app.app_context():
        Attempt.query.one().user_id=app.config['TEST_TEACHER'];db.session.commit()
    assert read(app,body).status_code==404


@pytest.mark.parametrize('raw',[
    {'verdict':'supported','reason':'adequate','checks':{'cause_explained':True,'connects_input_and_difference':True,'consistent_with_results':True},'quotes':['fabricated quote']},
    {'verdict':'supported','reason':'adequate','checks':{'cause_explained':True,'connects_input_and_difference':True,'consistent_with_results':True},'quotes':['错误版遗漏最后一个元素'],'counterexample_found':False},
    {'verdict':'uncertain','reason':'uncertain','checks':{'cause_explained':False,'connects_input_and_difference':False,'consistent_with_results':False},'quotes':[]}
])
def test_untrusted_model_output_never_changes_facts_or_becomes_feedback(app,raw):
    app.config['TUTOR_MODELS_ENABLED']=True
    facts={'counterexample_found':True,'expected_output_correct':True,'correct_result':{'kind':'value','value':5},'buggy_result':{'kind':'value','value':2}}
    with app.app_context(),patch('app.services.counterexample_explanation.get_llm_provider',return_value=Provider(raw)):
        answer=evaluate_explanation('sum',proposed()['buggy_code'],[2,3],EXPLANATION,facts)
    assert answer['status']=='needs_teacher' and 'fabricated quote' not in str(answer)
    assert facts['counterexample_found'] and facts['correct_result']['value']==5


def test_formal_followup_clears_practice_due_without_challenge_mastery_inflation(app):
    row=publish(app);body=body_for(row)
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run): submit(app,row,body)
    with app.app_context():
        State.drain()
        first=State.snapshot(app.config['TEST_STUDENT'])['concepts'][0]
        State.append(user_id=app.config['TEST_STUDENT'],kind='submission_graded',source_type='trial_question_progress',
            source_id='followup',source_version='1',occurred_at=utc_now()+timedelta(days=2),
            payload={'concept_id':first['concept_id'],'correct':True,'assisted':False,'evidence_scope':'server_graded'})
        db.session.commit();State.drain()
        concept=State.snapshot(app.config['TEST_STUDENT'])['concepts'][0]
        assert concept['counterexample_review_due_at'] is None
        assert concept['independent_count']==1 and concept['counterexample_success']==1
        assert concept['estimate']==round(2/3,4)


def test_attempt_migration_upgrade_downgrade_and_preserves_existing_state(app):
    path=Path(__file__).parents[1]/'migrations/versions/20261016_0024_counterexample_attempts.py'
    spec=importlib.util.spec_from_file_location('attempt_migration',path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with app.app_context(),db.engine.begin() as conn:
        operations=Operations(MigrationContext.configure(conn))
        before=conn.exec_driver_sql('SELECT COUNT(*) FROM users').scalar_one()
        with patch.object(migration,'op',operations):
            migration.downgrade();migration.upgrade();migration.upgrade()
        assert conn.exec_driver_sql('SELECT COUNT(*) FROM users').scalar_one()==before
        assert set(Attempt.__table__.columns.keys())=={c['name'] for c in inspect(conn).get_columns('counterexample_attempts')}
