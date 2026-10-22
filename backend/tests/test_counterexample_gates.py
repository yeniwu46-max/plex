"""Publication invariants: static contracts, independent tests, versions and leases."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
from threading import Event
from unittest.mock import patch
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask_jwt_extended import create_access_token
from sqlalchemy import inspect

from test_learner_state import app
from app.models import db, User, Class
from app.models.counterexample import CounterexampleSpec, CounterexampleChallenge, CounterexampleVersion, CounterexampleValidation
from app.services.counterexample_contract import candidate, specification, check_value, CounterexampleError, digest, python_function
from app.services.counterexample_validation import validate, HARNESS
from app.services.execution_errors import ExecutionUnavailable
from app.utils.time import utc_now


def uid(): return str(uuid.uuid4())


def spec_body():
    return {'title':'求和的反例挑战', 'statement':'函数应返回输入整数数组所有元素之和，空数组返回 0。',
        'concept_id':'loop-for', 'input_contract':{'type':'integer_array','minimum':-10,'maximum':10,'min_items':0,'max_items':10},
        'output_contract':{'type':'integer','minimum':-100,'maximum':100},
        'reference_code':'def solve(data):\n    return sum(data)',
        'tests':[{'input':[],'expected':0},{'input':[1],'expected':1},{'input':[1,2],'expected':3}],
        'reference_note':'教师人工核对求和定义及独立预期输出。', 'allowed_bug_exceptions':[]}


def proposed():
    return {'buggy_code':'def solve(data):\n    return sum(data[:-1])', 'fixed_code':spec_body()['reference_code'],
            'bug_kind':'loop_boundary', 'explanation':'错误版遗漏最后一个元素。'}


def auth(app, kind='teacher'):
    with app.app_context():
        identity = User.query.filter(User.role.has(name='admin')).first().id if kind=='admin' else app.config['TEST_TEACHER' if kind=='teacher' else 'TEST_STUDENT']
        return {'Authorization':'Bearer '+create_access_token(identity=str(identity))}


def call(app, path, body, kind='teacher'):
    return app.test_client().post('/api/v1/'+path, headers=auth(app,kind), json=body)


def make_challenge(app):
    with app.app_context(): cohort = db.session.get(User, app.config['TEST_STUDENT']).class_id
    spec = call(app,'teacher/counterexample-specifications',{'request_id':uid(),'class_id':cohort,'specification':spec_body()})
    assert spec.status_code == 200, spec.json
    result = call(app,'teacher/counterexample-challenges',{'request_id':uid(),'spec_id':spec.json['data']['id'],'candidate':proposed()})
    assert result.status_code == 200, result.json
    return result.json['data']


def validate_body(row): return {'request_id':uid(), 'manifest_hash':row['manifest_hash']}


def validation_path(row): return 'teacher/counterexample-challenges/'+row['id']+'/validate'


def public(app,row,kind='student'):
    return app.test_client().get('/api/v1/student/counterexample-challenges/'+row['id'],headers=auth(app,kind))


def review_body(row, report_id):
    return {'action':'publish','manifest_hash':row['manifest_hash'],'validation_id':report_id,'note':'已核对单一边界错误、题意、解释和难度。',
        'checks':{key:True for key in ('single_clear_bug','statement_consistent','explanation_correct','difficulty_appropriate')}}


def review(app,row,body): return call(app,'teacher/counterexample-challenges/'+row['id']+'/review',body)


PASSED = {'passed':True,'witnesses':[{'test_index':1,'input':[1],'buggy':{'value':0},'reference':{'value':1}}],
          'reason':None,'scope':'declared_tests_only'}


def fake_run(_language, code, stdin):
    assert code == HARNESS
    data = json.loads(stdin)
    assert set(data) == {'source','inputs'} and 'expected' not in stdin
    results = [{'kind':'value','value':sum(value[:-1] if '[:-1]' in data['source'] else value)} for value in data['inputs']]
    return {'status':{'id':3}, 'stdout':json.dumps({'python':'3.12.10','results':results}),
            'backend':'docker','image_id':'sha256:verified-test-image'}


@pytest.mark.parametrize('source', [
    'print(1)', 'def solve(data):\n import os\n return 0',
    'def solve(data):\n return eval("1")', 'def solve(data):\n return data.__class__',
    'def solve(data):\n return open("/tmp/result")', 'def solve(data=print(1)):\n return data',
    'def solve(data):\n def inner(): return 1\n return inner()',
    '@print(1)\ndef solve(data):\n return 1', 'def solve(data):\n while',
])
def test_static_contract_never_executes_program(source):
    with patch('subprocess.Popen') as host, pytest.raises(CounterexampleError):
        python_function(source)
    assert not host.called


def test_input_contract_rejects_boolean_disguised_as_integer_and_illegal_empty():
    contract = {'type':'integer_array','minimum':0,'maximum':3,'min_items':1,'max_items':2}
    for bad in ([], [True], [4], [1,2,3], '[]', {'0':1}): assert not check_value(bad,contract)
    assert check_value([0,3],contract)
    body = spec_body(); body['tests'][1] = deepcopy(body['tests'][0])
    with pytest.raises(CounterexampleError): specification(body)
    body=spec_body(); body['tests'][0]['expected']=False
    with pytest.raises(CounterexampleError): specification(body)
    with pytest.raises(CounterexampleError): python_function('def solve(data):\n    return 0 # '+ '中'*5400)


def test_differential_gate_checks_reference_and_repeats_in_separate_runs():
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=fake_run) as runner:
        result=validate(specification(spec_body()),candidate(proposed()))
    assert result['passed'] and len(result['witnesses'])==2 and runner.call_count==6
    assert result['runtimes'][0]['image_id']=='sha256:verified-test-image'
    assert result['scope']=='declared_tests_only'
    assert result['artifact_hashes']['tests']==digest(spec_body()['tests'])


@pytest.mark.parametrize('case,reason', [
    ('reference','reference_test_mismatch'),('fixed','fixed_test_mismatch'),('same','no_counterexample'),
    ('non_deterministic','non_deterministic'),('timeout','execution_timeout'),('image','missing_runtime_identity'),
    ('output','buggy_output_contract'),('exception','buggy_exception'),('runtime','runtime_changed')])
def test_bad_material_never_passes(case,reason):
    spec=spec_body(); proposal=proposed(); count=0
    if case=='reference': spec['tests'][1]['expected']=9
    if case=='fixed': proposal['fixed_code']=proposal['buggy_code']
    if case=='same': proposal['buggy_code']=proposal['fixed_code']
    def run(*args):
        nonlocal count
        count+=1; result=fake_run(*args)
        if case=='timeout': result['status']={'id':5}
        if case=='image': result.pop('image_id')
        if case=='runtime' and count==2: result['image_id']='different-image'
        payload=json.loads(result['stdout'])
        if case=='non_deterministic' and count==2: payload['results'][0]['value']=1
        if case=='output' and count in (5,6): payload['results'][0]['value']=True
        if case=='exception' and count in (5,6): payload['results'][0]={'kind':'exception','exception':'IndexError'}
        result['stdout']=json.dumps(payload)
        return result
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=run): result=validate(specification(spec),candidate(proposal))
    assert not result['passed'] and result['reason']==reason


def test_explicit_exception_is_a_witness_but_infrastructure_is_not():
    spec=spec_body(); spec['allowed_bug_exceptions']=['IndexError']
    def run(*args):
        result=fake_run(*args)
        if '[:-1]' in json.loads(args[2])['source']:
            payload=json.loads(result['stdout']);payload['results'][0]={'kind':'exception','exception':'IndexError'}
            result['stdout']=json.dumps(payload)
        return result
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=run):
        assert validate(specification(spec),candidate(proposed()))['passed']
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=ExecutionUnavailable()),pytest.raises(ExecutionUnavailable):
        validate(specification(spec),candidate(proposed()))


def test_publication_requires_gate_and_full_teacher_review_then_strips_secrets(app):
    row=make_challenge(app)
    assert public(app,row).status_code==404
    assert review(app,row,review_body(row,uid())).status_code==409
    body=validate_body(row)
    with patch('app.services.counterexample.validate',return_value=PASSED) as runner:
        validated=call(app,validation_path(row),body)
        assert validated.status_code==200,validated.json
        assert call(app,validation_path(row),body).json==validated.json
        assert runner.call_count==1
    bad=review_body(row,body['request_id']);bad['checks']['single_clear_bug']=False
    assert review(app,row,bad).status_code==400
    assert review(app,row,review_body(row,body['request_id'])).status_code==200
    assert review(app,row,review_body(row,body['request_id'])).status_code==200
    response=public(app,row);assert response.status_code==200
    data=response.json['data']
    assert data['buggy_code']==proposed()['buggy_code']
    for secret in ('fixed_code','reference_code','tests','witnesses','explanation','reference_note','validation','candidate'):
        assert secret not in data
    with app.app_context():
        assert CounterexampleValidation.query.count()==1
        db.session.get(User,app.config['TEST_STUDENT']).class_id=None;db.session.commit()
    assert public(app,row).status_code==404


def test_failed_or_unavailable_validation_cannot_be_approved(app):
    row=make_challenge(app);body=validate_body(row)
    with patch('app.services.counterexample.validate',side_effect=ExecutionUnavailable('busy')):
        response=call(app,validation_path(row),body)
    assert response.status_code==503 and response.json['data']['retryable']
    assert review(app,row,review_body(row,body['request_id'])).status_code==409
    with app.app_context(): assert CounterexampleValidation.query.one().status=='unavailable'
    with patch('app.services.counterexample.validate',return_value={'passed':False,'reason':'fixed_test_mismatch'}):
        response=call(app,validation_path(row),body)
    assert response.status_code==200 and response.json['data']['status']=='failed'
    assert review(app,row,review_body(row,body['request_id'])).status_code==409
    assert call(app,'teacher/counterexample-challenges/'+row['id']+'/review',review_body(row,body['request_id']),'admin').status_code==409


def test_new_revision_is_immutable_unpublished_and_cannot_reuse_old_report(app):
    row=make_challenge(app);body=validate_body(row)
    with patch('app.services.counterexample.validate',return_value=PASSED): call(app,validation_path(row),body)
    assert review(app,row,review_body(row,body['request_id'])).status_code==200
    changed=proposed(); changed['explanation']='教师重新核对：遗漏末尾值。'
    revision={'request_id':uid(),'expected_revision':1,'spec_id':row['spec_id'],'candidate':changed}
    endpoint='teacher/counterexample-challenges/'+row['id']+'/versions'
    result=call(app,endpoint,revision); assert result.status_code==200,result.json
    revised=result.json['data'];assert revised['current_revision']==2 and revised['manifest_hash']!=row['manifest_hash']
    assert call(app,endpoint,revision).json==result.json
    assert call(app,endpoint,{**revision,'request_id':uid()}).status_code==409
    assert public(app,row).status_code==404
    assert review(app,revised,review_body(revised,body['request_id'])).status_code==409
    assert review(app,row,{'action':'withdraw','manifest_hash':row['manifest_hash']}).status_code==409
    with app.app_context():
        assert CounterexampleVersion.query.count()==2
        assert CounterexampleVersion.query.filter_by(revision=1).one().candidate==proposed()


def test_revalidation_withdraws_old_publication_and_stale_worker_cannot_publish(app):
    row=make_challenge(app);first=validate_body(row)
    with patch('app.services.counterexample.validate',return_value=PASSED): call(app,validation_path(row),first)
    review(app,row,review_body(row,first['request_id']))
    entered,release=Event(),Event()
    def slow(*args): entered.set();assert release.wait(12);return PASSED
    second=validate_body(row)
    with patch('app.services.counterexample.validate',side_effect=slow) as runner,ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(call,app,validation_path(row),second)
        try:
            assert entered.wait(12)
            assert public(app,row).status_code==404
            assert call(app,validation_path(row),second).status_code==409
            assert call(app,validation_path(row),validate_body(row)).status_code==409
            assert review(app,row,review_body(row,first['request_id'])).status_code==409
        finally: release.set()
        assert pending.result(timeout=15).status_code==200 and runner.call_count==1


def test_version_changed_while_validation_runs_is_not_publishable(app):
    row=make_challenge(app);body=validate_body(row)
    def changed(*args):
        result=call(app,'teacher/counterexample-challenges/'+row['id']+'/versions',
            {'request_id':uid(),'expected_revision':1,'spec_id':row['spec_id'],'candidate':proposed()})
        assert result.status_code==200
        return PASSED
    with patch('app.services.counterexample.validate',side_effect=changed):
        assert call(app,validation_path(row),body).status_code==409
    with app.app_context(): assert CounterexampleValidation.query.one().status=='superseded'


def test_expired_validation_worker_cannot_overwrite_recovered_report(app):
    row=make_challenge(app);body=validate_body(row)
    def expire_and_retry(*args):
        record=db.session.get(CounterexampleValidation,body['request_id'])
        record.lease_until=utc_now()-timedelta(seconds=1);db.session.commit()
        with patch('app.services.counterexample.validate',return_value=PASSED):
            recovered=call(app,validation_path(row),body)
        assert recovered.status_code==200,recovered.json
        return {'passed':False,'reason':'old_worker_must_not_win'}
    with patch('app.services.counterexample.validate',side_effect=expire_and_retry):
        response=call(app,validation_path(row),body)
    assert response.status_code==409
    with app.app_context():
        record=CounterexampleValidation.query.one()
        assert record.status=='passed' and record.report['passed']


def test_ownership_roles_and_manifest_tampering(app):
    row=make_challenge(app)
    assert call(app,validation_path(row),validate_body(row),'student').status_code==403
    with app.app_context():
        other=User.query.filter(User.id.notin_([app.config['TEST_STUDENT'],app.config['TEST_TEACHER']])).first()
        cohort=db.session.get(Class,row['class_id']);cohort.teacher_id=other.id;db.session.commit()
    assert call(app,validation_path(row),validate_body(row)).status_code==404
    with app.app_context():
        db.session.get(Class,row['class_id']).teacher_id=app.config['TEST_TEACHER']
        version=CounterexampleVersion.query.one();version.candidate={**version.candidate,'explanation':'changed outside versioning'};db.session.commit()
    with patch('app.services.counterexample.validate') as runner:
        assert call(app,validation_path(row),validate_body(row)).status_code==409
        assert not runner.called


def test_migration_upgrade_twice_and_downgrade(app):
    path=Path(__file__).parents[1]/'migrations/versions/20261016_0023_counterexample_gates.py'
    spec=importlib.util.spec_from_file_location('counterexample_migration',path)
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    next_spec=importlib.util.spec_from_file_location('attempt_migration',path.with_name('20261016_0024_counterexample_attempts.py'))
    next_migration=importlib.util.module_from_spec(next_spec);next_spec.loader.exec_module(next_migration)
    generation_spec=importlib.util.spec_from_file_location('generation_migration',path.with_name('20261016_0025_counterexample_generation.py'))
    generation_migration=importlib.util.module_from_spec(generation_spec);generation_spec.loader.exec_module(generation_migration)
    catalog_spec=importlib.util.spec_from_file_location('catalog_migration',path.with_name('20261017_0026_counterexample_catalog.py'))
    catalog_migration=importlib.util.module_from_spec(catalog_spec);catalog_spec.loader.exec_module(catalog_migration)
    with app.app_context(),db.engine.begin() as conn:
        operations=Operations(MigrationContext.configure(conn))
        with patch.object(catalog_migration,'op',operations):
            catalog_migration.downgrade()
        with patch.object(generation_migration,'op',operations):
            generation_migration.downgrade()
        with patch.object(next_migration,'op',operations):
            next_migration.downgrade()
        with patch.object(migration,'op',operations):
            migration.downgrade();migration.upgrade();migration.upgrade()
        with patch.object(next_migration,'op',operations):
            next_migration.upgrade()
        with patch.object(generation_migration,'op',operations):
            generation_migration.upgrade();generation_migration.upgrade()
        with patch.object(catalog_migration,'op',operations):
            catalog_migration.upgrade();catalog_migration.upgrade()
        from app.models.counterexample import CounterexampleGenerationTask, CounterexampleGenerationCall
        for model in (CounterexampleGenerationTask, CounterexampleGenerationCall):
            assert {c['name'] for c in inspect(conn).get_columns(model.__tablename__)}==set(model.__table__.columns.keys())
        assert set(('counterexample_specs','counterexample_challenges','counterexample_versions','counterexample_validations')) <= set(inspect(conn).get_table_names())
        assert {c['name'] for c in inspect(conn).get_columns('counterexample_versions')}==set(CounterexampleVersion.__table__.columns.keys())
