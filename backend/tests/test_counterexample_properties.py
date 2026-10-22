"""Finite property plans, independent oracles, legacy hashes and hard gates."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from test_counterexample_gates import app, spec_body, proposed, uid, call, review, review_body, public
from app.models import db, User
from app.services.counterexample_contract import specification, candidate, CounterexampleError, digest, check_value
from app.services.counterexample_properties import POLICY, build_plan, PROPERTY_IDS
from app.services.counterexample_validation import validate, run_suite, HARNESS

RUNTIME = {'backend':'docker','python':'3.12.15','image_id':'sha256:property-fixture','harness_hash':digest(HARNESS)}


def extended(properties=(), *, boundary=True):
    spec=spec_body()
    spec['verification']={'policy_version':POLICY,'boundary_checks':boundary,'properties':list(properties),
        'rationale':'按题意人工确认合法输入范围及所选关系。'}
    return spec


def fixture_run(functions):
    def run(source,inputs):
        # Fixtures map known source strings to test oracles; no eval/exec.
        outcomes=[]
        for value in inputs:
            try: outcomes.append({'kind':'value','value':functions[source](deepcopy(value))})
            except (ValueError,IndexError) as exc: outcomes.append({'kind':'exception','exception':type(exc).__name__})
        return outcomes,deepcopy(RUNTIME)
    return run


def sum_runner(spec, proposal):
    return fixture_run({spec['reference_code']:sum,proposal['fixed_code']:sum,
                        proposal['buggy_code']:lambda value:sum(value[:-1])})


def test_legacy_hash_stays_stable_and_opt_in_has_new_contract():
    legacy=specification(spec_body())
    assert legacy['contract_version']=='counterexample-v1' and 'verification' not in legacy
    assert digest(legacy)==digest(specification({k:v for k,v in legacy.items() if k!='contract_version'}))
    upgraded=specification(extended())
    assert upgraded['contract_version']=='counterexample-v2' and digest(upgraded)!=digest(legacy)
    assert specification({k:v for k,v in upgraded.items() if k!='contract_version'})==upgraded


@pytest.mark.parametrize('change', ['unknown','duplicate','non_boolean','unconfirmed','missing_empty','integer_input','array_output','inapplicable'])
def test_invalid_property_contract_is_rejected_before_any_execution(change):
    spec=extended(['permutation_invariant'])
    if change=='unknown':spec['verification']['properties']=['execute_arbitrary_code']
    if change=='duplicate':spec['verification']['properties']*=2
    if change=='non_boolean':spec['verification']['boundary_checks']=1
    if change=='unconfirmed':spec['verification']['rationale']=''
    if change=='missing_empty':spec['tests'][0]={'input':[2],'expected':2}
    if change=='integer_input':
        spec['input_contract']={'type':'integer','minimum':-10,'maximum':10}
        spec['tests']=[{'input':x,'expected':x} for x in (0,1,2)]
    if change=='array_output':
        spec['verification']['properties']=['result_is_member']
        spec['output_contract']={'type':'integer_array','minimum':-100,'maximum':100,'min_items':0,'max_items':10}
        spec['tests']=[{'input':case['input'],'expected':[case['expected']]} for case in spec['tests']]
    if change=='inapplicable':
        spec['input_contract'].update(min_items=2,max_items=2)
        spec['tests']=[{'input':[x,x],'expected':2*x} for x in (0,1,2)]
        spec['verification']['properties']=['duplicate_invariant']
    with patch('app.services.counterexample_validation.run_function') as execute,pytest.raises(CounterexampleError):specification(spec)
    assert not execute.called


def test_plan_is_repeatable_bounded_and_uses_only_legal_inputs():
    spec=specification(extended(PROPERTY_IDS))
    plan=build_plan(spec['input_contract'],spec['tests'],spec['verification'])
    assert plan==build_plan(spec['input_contract'],deepcopy(spec['tests']),deepcopy(spec['verification']))
    assert 3<len(plan['inputs'])<=64
    assert len({digest(value) for value in plan['inputs']})==len(plan['inputs'])
    assert all(check_value(value,spec['input_contract']) for value in plan['inputs'])
    for key in PROPERTY_IDS: assert 1<=sum(row['property']==key for row in plan['relations'])<=4
    assert [] in plan['inputs'] and [-10]*10 in plan['inputs'] and [10]*10 in plan['inputs']
    assert len(plan['inputs'])==len(plan['origins'])


def test_sum_passes_appropriate_relations_but_buggy_program_need_not_obey_them():
    spec=specification(extended(['permutation_invariant','append_zero_invariant','concatenation_additive']))
    proposal=candidate(proposed())
    with patch('app.services.counterexample_validation.run_function',side_effect=sum_runner(spec,proposal)):
        result=validate(spec,proposal)
    assert result['passed'] and result['scope']=='declared_and_bounded_checks'
    assert all(item['failed']==0 for item in result['coverage']['properties'])
    assert {item['program'] for item in result['coverage']['properties']}=={'reference','fixed'}
    assert result['witness_count']>=len(result['witnesses']) and len(result['witnesses'])<=8
    assert result['artifact_hashes']['verification']==digest(spec['verification'])


def test_same_wrong_reference_and_fixed_are_detected_by_declared_relation():
    spec=extended(['permutation_invariant'])
    spec['reference_code']='def solve(data):\n    return data[0] if data else 0'
    spec['tests']=[{'input':[],'expected':0},{'input':[1],'expected':1},{'input':[2,2],'expected':2}]
    proposal={**proposed(),'fixed_code':spec['reference_code']}
    with patch('app.services.counterexample_validation.run_function',side_effect=fixture_run({
            spec['reference_code']:lambda values:values[0] if values else 0,
            proposal['buggy_code']:lambda values:sum(values[:-1])})):
        result=validate(spec,proposal)
    assert not result['passed'] and result['reason']=='reference_property_mismatch'
    failure=result['coverage']['failures'][0]
    assert failure['base_output']!=failure['derived_output'] and failure['base_input']!=failure['derived_input']


def test_false_teacher_claim_does_not_get_silently_dropped():
    spec=specification(extended(['duplicate_invariant']))
    proposal=proposed()
    with patch('app.services.counterexample_validation.run_function',side_effect=sum_runner(spec,proposal)):
        result=validate(spec,proposal)
    assert not result['passed'] and result['reason']=='reference_property_mismatch'
    assert result['coverage']['failures'][0]['property']=='duplicate_invariant'


@pytest.mark.parametrize('kind', ['duplicate','membership'])
def test_distinct_sum_and_maximum_can_check_their_respective_properties(kind):
    spec=extended(['duplicate_invariant'] if kind=='duplicate' else ['result_is_member','permutation_invariant'])
    reference='def solve(data):\n    return sum(set(data))' if kind=='duplicate' else 'def solve(data):\n    return max(data) if data else 0'
    fn=(lambda values:sum(set(values))) if kind=='duplicate' else (lambda values:max(values) if values else 0)
    wrong='def solve(data):\n    return sum(data)' if kind=='duplicate' else 'def solve(data):\n    return max(data)'
    spec.update(reference_code=reference,tests=[{'input':x,'expected':fn(x)} for x in ([],[2,2],[1,3])],allowed_bug_exceptions=[] if kind=='duplicate' else ['ValueError'])
    proposal={**proposed(),'fixed_code':reference,'buggy_code':wrong}
    with patch('app.services.counterexample_validation.run_function',side_effect=fixture_run({reference:fn,
            wrong:sum if kind=='duplicate' else max})):
        result=validate(spec,proposal)
    assert result['passed'] and all(row['failed']==0 for row in result['coverage']['properties'])


def test_sample_overfit_is_caught_on_generated_boundary_not_labeled_independent_answer():
    spec=specification(extended())
    proposal={**proposed(),'fixed_code':'def solve(data):\n    return sum(data) if len(data)<3 else 0'}
    with patch('app.services.counterexample_validation.run_function',side_effect=fixture_run({
            spec['reference_code']:sum,proposal['fixed_code']:lambda values:sum(values) if len(values)<3 else 0,
            proposal['buggy_code']:lambda values:sum(values[:-1])})):
        result=validate(spec,proposal)
    assert not result['passed'] and result['reason']=='fixed_reference_mismatch'
    assert result['failure_detail']['input_origin']=='boundary'
    assert result['failure_detail']['expected']['value']!=result['failure_detail']['observed']['value']


def test_large_legal_suite_is_chunked_without_sharing_expected_values():
    inputs=[[x]*128 for x in range(64)]
    packets=[]
    def execute(_lang,code,stdin):
        packet=json.loads(stdin);packets.append(packet)
        assert code==HARNESS and len(stdin.encode('utf-8'))<=60000 and len(packet['inputs'])<=24
        assert set(packet)=={'source','inputs'}
        return {'status':{'id':3},'backend':'docker','image_id':'sha256:test',
            'stdout':json.dumps({'python':'3.12.15','results':[{'kind':'value','value':x} for x in packet['inputs']]})}
    with patch('app.services.counterexample_validation.CodeExecutionService.run',side_effect=execute):
        outcomes,_,count=run_suite('def solve(data):\n    return data',inputs)
    assert count==3 and [item['value'] for item in outcomes]==inputs
    assert [value for packet in packets for value in packet['inputs']]==inputs


def test_properties_are_versioned_private_and_cannot_bypass_publication(app):
    with app.app_context():cohort=db.session.get(User,app.config['TEST_STUDENT']).class_id
    spec=extended(['duplicate_invariant'])
    saved=call(app,'teacher/counterexample-specifications',{'request_id':uid(),'class_id':cohort,'specification':spec})
    assert saved.status_code==200,saved.json
    created=call(app,'teacher/counterexample-challenges',{'request_id':uid(),'spec_id':saved.json['data']['id'],'candidate':proposed()}).json['data']
    validation_id=uid()
    with patch('app.services.counterexample_validation.run_function',side_effect=sum_runner(spec,proposed())):
        result=call(app,'teacher/counterexample-challenges/'+created['id']+'/validate',{'request_id':validation_id,'manifest_hash':created['manifest_hash']})
    assert result.json['data']['status']=='failed'
    assert review(app,created,review_body(created,validation_id)).status_code==409
    assert public(app,created).status_code==404
    updated=extended(['permutation_invariant'])
    changed=call(app,'teacher/counterexample-specifications',{'request_id':saved.json['data']['id'],'class_id':cohort,'specification':updated})
    assert changed.status_code==409
    new_basis=call(app,'teacher/counterexample-specifications',{'request_id':uid(),'class_id':cohort,'specification':updated}).json['data']
    revised=call(app,'teacher/counterexample-challenges/'+created['id']+'/versions',{'request_id':uid(),'expected_revision':1,'spec_id':new_basis['id'],'candidate':proposed()}).json['data']
    assert revised['manifest_hash']!=created['manifest_hash']
    validation_id=uid()
    with patch('app.services.counterexample_validation.run_function',side_effect=sum_runner(updated,proposed())):
        result=call(app,'teacher/counterexample-challenges/'+created['id']+'/validate',{'request_id':validation_id,'manifest_hash':revised['manifest_hash']})
    assert result.json['data']['status']=='passed'
    assert review(app,revised,review_body(revised,validation_id)).status_code==200
    assert 'verification' not in public(app,revised).json['data']
