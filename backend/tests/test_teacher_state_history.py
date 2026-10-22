"""Synthetic declarations and fake model outputs in temporary test files only."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from unittest.mock import patch

from flask import Flask
import pytest

from scripts import teacher_state_history as history
from scripts.teacher_baseline_contract import ContractError, read_json
from scripts.evaluate_teacher_baseline import run, isolated_course, new_student
from scripts.check_teacher_answers import check, load_run
from test_teacher_evaluation import artifact, provider, Transport
from test_teacher_answer_review import fill


def package(baseline):
    value=history.template(baseline)
    value['as_of']=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    value['reviewers']=[{'id':'test-only-person','declares_python_teaching_experience':True,
        'declares_personal_review':True,'declares_data_use_permission':True}]
    for row in value['histories']:
        row['observations']=[{'id':str(i),'kind':'grade','concept_id':'loop-for',
            'at':(history.timestamp(value['as_of'])-timedelta(days=2-i)).isoformat(),
            'correct':False,'assisted':False,'mode':None,'due_at':None,'source_sha256':None} for i in range(2)]
        row.update(accepted=True, reviewer_id='test-only-person',reviewed_at=datetime.now(timezone.utc).isoformat(),
            rationale='SYNTHETIC TEST FIXTURE; no actual human decision',expected_adjustment='HISTORY_GOLD_SECRET_SENTINEL')
    return value


def frozen(baseline,tmp_path):
    return history.freeze(baseline,package(baseline),tmp_path/'history.json')


def test_template_has_no_observations_or_fabricated_reviews(tmp_path):
    data=artifact(tmp_path); value=history.template(data)
    report=history.validate(data,value)
    assert report['pending']==120 and report['accepted']==0 and not report['ready_to_freeze']
    assert not value['reviewers'] and all(not r['observations'] and r['accepted'] is None for r in value['histories'])
    with pytest.raises(ContractError): history.freeze(data,value,tmp_path/'forbidden.json')
    assert not (tmp_path/'forbidden.json').exists()


def test_frozen_history_is_bound_to_cases_baseline_and_content(tmp_path):
    data=artifact(tmp_path); value=frozen(data,tmp_path)
    assert len(history.verify(data,value))==120
    with pytest.raises(FileExistsError): history.freeze(data,package(data),tmp_path/'history.json')
    value['package']['histories'][0]['observations'][0]['correct']=True
    with pytest.raises(ContractError,match='changed'): history.verify(data,value)


@pytest.mark.parametrize('kind', ['baseline','case','extra','bool','future','order','duplicate','concept',
    'review_grade','hint','cross_split','conflicting_group','reviewer','review_future','no_adjustment','empty',
    'real_without_source','provenance_type','extra_personal_data'])
def test_invalid_histories_rejected_before_any_replay(tmp_path,kind):
    data=artifact(tmp_path); value=package(data); row=value['histories'][0];event=row['observations'][0]
    if kind=='baseline': value['baseline_sha256']='a'*64
    if kind=='case': row['case_sha256']='a'*64
    if kind=='extra': event['student_email']='do-not-accept@example.invalid'
    if kind=='bool': event['correct']=1
    if kind=='future': event['at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    if kind=='order': row['observations'].reverse()
    if kind=='duplicate': row['observations'][1]['id']=event['id']
    if kind=='concept': event['concept_id']='invented-concept'
    if kind=='review_grade': event['kind']='review_schedule'
    if kind=='hint': event.update(kind='hint',correct=None,assisted=None,mode='complete_answer')
    if kind=='cross_split':
        test_ids={c['id'] for c in data['case_pack']['cases'] if c['split']=='test'}
        next(r for r in value['histories'] if r['case_id'] in test_ids)['history_id']=row['history_id']
    if kind=='conflicting_group': value['histories'][1]['observations'][0]['correct']=True
    if kind=='reviewer': row['reviewer_id']='unknown'
    if kind=='review_future': row['reviewed_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    if kind=='no_adjustment': row['expected_adjustment']=None
    if kind=='empty':
        for item in value['histories']: item['observations']=[]
    if kind=='real_without_source': value['provenance']='declared_deidentified_observations'
    if kind=='provenance_type': value['provenance']=[]
    if kind=='extra_personal_data': value['account_export']=[]
    with pytest.raises(ContractError): history.validate(data,value)


def test_declared_real_history_requires_permission_and_cannot_cross_splits(tmp_path):
    import hashlib
    data=artifact(tmp_path); value=package(data);value['provenance']='declared_deidentified_observations'
    for row in value['histories']:
        for e in row['observations']:
            e['source_sha256']=hashlib.sha256((row['history_id']+'/'+e['id']).encode()).hexdigest()
    assert not history.validate(data,value)['ready_to_freeze']
    value['permission_reference']='TEST-FIXTURE-permission-declaration'
    report=history.validate(data,value)
    assert report['ready_to_freeze'] and report['identity_and_origin_authenticated'] is False
    test_ids={c['id'] for c in data['case_pack']['cases'] if c['split']=='test'}
    next(r for r in value['histories'] if r['case_id'] in test_ids)['observations'][0]['source_sha256']=value['histories'][0]['observations'][0]['source_sha256']
    with pytest.raises(ContractError,match='crosses'): history.validate(data,value)


@pytest.mark.parametrize('mutation',['duplicate_source','different_facts'])
def test_same_source_digest_cannot_inflate_or_change_declared_history(tmp_path,mutation):
    import hashlib
    data=artifact(tmp_path);value=package(data)
    for row in value['histories']:
        for event in row['observations']:
            event['source_sha256']=hashlib.sha256((row['history_id']+'/'+event['id']).encode()).hexdigest()
    if mutation=='duplicate_source':
        value['histories'][0]['observations'][1]['source_sha256']=value['histories'][0]['observations'][0]['source_sha256']
    else:
        value['histories'][1]['history_id']='different-history'
        value['histories'][1]['observations'][0]['correct']=True
    with pytest.raises(ContractError): history.validate(data,value)


def test_replay_denied_outside_disposable_course(tmp_path):
    app=Flask('not-an-evaluation')
    with app.app_context(),pytest.raises(ContractError,match='isolated'):
        history.replay(1,{},datetime.now(timezone.utc).isoformat())


def test_replay_uses_current_projection_unknowns_and_fixed_as_of(tmp_path):
    from app.services.learner_state import LearnerStateService as State
    from app.services.learner_decision import LearnerDecisionService
    data=artifact(tmp_path); value=package(data); row=value['histories'][0]
    (tmp_path/'course').mkdir()
    with isolated_course(data,tmp_path/'course',allow_history=True):
        uid=new_student('case','history')
        snapshot=history.replay(uid,row,value['as_of'])
        assert snapshot['state_version']==2 and snapshot['concepts'][0]['independent_count']==2
        assert snapshot['concepts'][0]['independent_success']==0 and snapshot['concepts'][0]['estimate']==.25
        assert snapshot['misconceptions']==[] and snapshot['concepts'][0]['hints_seen']==0
        with history.decision_clock(value['as_of']):
            decision=LearnerDecisionService.from_snapshot(snapshot)
        assert decision['basis']=='formal_evidence'
        with pytest.raises(ContractError,match='fresh'): history.replay(uid,row,value['as_of'])
        assert State.snapshot(uid)['state_version']==2


def test_hint_review_and_staleness_use_declared_time_without_inventing_success(tmp_path):
    from app.services.learner_decision import LearnerDecisionService
    data=artifact(tmp_path);value=package(data);as_of=history.timestamp(value['as_of'])
    for row in value['histories']:
        for index,event in enumerate(row['observations']):
            event['at']=(as_of-timedelta(days=40-index)).isoformat()
        row['observations'] += [
            {'id':'hint-1','kind':'hint','concept_id':'loop-for','at':(as_of-timedelta(hours=12)).isoformat(),
             'correct':None,'assisted':None,'mode':'next_step','due_at':None,'source_sha256':None},
            {'id':'review-1','kind':'review_schedule','concept_id':'loop-for','at':(as_of-timedelta(hours=10)).isoformat(),
             'correct':None,'assisted':None,'mode':None,'due_at':(as_of-timedelta(hours=1)).isoformat(),'source_sha256':None}]
    assert history.validate(data,value)['ready_to_freeze']
    (tmp_path/'course').mkdir()
    with isolated_course(data,tmp_path/'course',allow_history=True):
        state=history.replay(new_student('case','history'),value['histories'][0],value['as_of'])
        concept=state['concepts'][0]
        assert state['state_version']==4 and concept['hints_seen']==concept['review_count']==1
        assert concept['estimate']==.25 and concept['independent_count']==2 and concept['stale'] is True
        with history.decision_clock(value['as_of']):
            assert LearnerDecisionService.from_snapshot(state)['basis']=='review_due'


@pytest.fixture
def comparison(tmp_path):
    data=artifact(tmp_path);hist=frozen(data,tmp_path);transport=Transport();client=provider(transport)
    output=tmp_path/'state-run'
    report=run(data,output,maximum_cases=1,provider=client,history_artifact=hist)
    return data,hist,output,report,transport


def test_paired_run_only_changes_snapshot_and_keeps_labels_out_of_model(comparison):
    data,hist,output,report,transport=comparison
    assert report['status']=='completed' and report['expected_results']==2 and report['physical_calls']==4
    manifest=read_json(output/'manifest.json')
    assert manifest['protocol']==history.PROTOCOL and manifest['arms']==list(history.ARMS)
    assert manifest['history_provenance']=='synthetic_scenarios'
    results=[read_json(p) for p in output.glob('result-*.json')]
    assert {r['projected_state']['state_version'] for r in results}=={2}
    assert {r['state_available'] for r in results}=={True,False}
    inputs=[json.loads(r['messages'][-1]['content']) for r in transport.requests]
    generated=[p for p in inputs if 'teaching_plan' in p]
    assert {p['teaching_plan']['state_version'] for p in generated}=={0,2}
    assert {p['teaching_plan']['decision']['basis'] for p in generated}=={'baseline','formal_evidence'}
    assert len({p['student_question'] for p in generated})==1
    assert all('GOLD_SECRET_SENTINEL' not in str(r) and 'test-only-person' not in str(r) for r in transport.requests)
    assert {r['temperature'] for r in transport.requests}=={.1}
    assert all(r['state_projection_is_new_measurement'] is False for r in results)
    review=read_json(output/'blind-review.json')
    assert len(review['items'])==2 and review['items'][0]['history_context']==review['items'][1]['history_context']
    assert check(output,review)['quality_metrics'] is None


def test_state_grading_requires_both_arms_and_reports_paired_descriptive_differences(comparison):
    _,_,output,_,_=comparison
    marked=fill(read_json(output/'blind-review.json'))
    report=check(output,marked)
    assert report['status']=='reviewed' and set(report['quality_metrics'])==set(history.ARMS)
    assert report['paired_state_differences']['metrics']['correctness']=={
        'mean_visible_minus_masked':0.,'pairs':1,'not_applicable_pairs':0}
    assert report['paired_state_differences']['metrics']['evidence_support']['not_applicable_pairs']==1
    assert report['causal_state_effect'] is None and report['learning_gain'] is None
    marked['items'][0]['history_context']['observations'][0]['correct']=True
    with pytest.raises(ContractError,match='changed'): check(output,marked)


def test_incomplete_model_pair_cannot_produce_quality_metrics(tmp_path):
    data=artifact(tmp_path);hist=frozen(data,tmp_path)
    output=tmp_path/'incomplete'
    report=run(data,output,maximum_cases=1,provider=provider(maximum=1),history_artifact=hist)
    assert report['status']!='completed' and report['unpaired_case_ids']
    marked=fill(read_json(output/'blind-review.json'))
    scored=check(output,marked)
    assert scored['quality_metrics'] is None and 'paired_state_differences' not in scored


def test_unreviewed_history_cannot_create_output_or_contact_provider(tmp_path):
    data=artifact(tmp_path);client=provider()
    with pytest.raises(ContractError):run(data,tmp_path/'forbidden',provider=client,history_artifact=history.template(data))
    assert not (tmp_path/'forbidden').exists() and client.calls==[]


def test_planning_is_network_free_and_marks_subset_history(tmp_path):
    data=artifact(tmp_path);hist=frozen(data,tmp_path)
    report=run(data,tmp_path/'plan',maximum_cases=1,history_artifact=hist)
    assert report['model_calls']==0
    manifest=read_json(tmp_path/'plan/manifest.json')
    assert manifest['planned_max_physical_calls']==4 and manifest['complete_split'] is False


def test_modes_that_read_more_than_snapshot_fail_comparison_without_model_calls(tmp_path):
    from app.services.messenger_tutoring import MessengerTutoring
    original=MessengerTutoring.prepare
    def overview(*args,**kwargs):
        payload=original(*args,**kwargs);payload['mode']='learning_overview';return payload
    data=artifact(tmp_path);hist=frozen(data,tmp_path);client=provider()
    with patch.object(MessengerTutoring,'prepare',side_effect=overview):
        report=run(data,tmp_path/'run',maximum_cases=1,provider=client,history_artifact=hist)
    assert report['status']=='completed_with_missing_pairs' and client.calls==[]
    assert all(read_json(p)['error_code']=='mode_reads_more_than_supplied_state' for p in (tmp_path/'run').glob('result-*.json'))
