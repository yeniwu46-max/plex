"""Trace contracts with mocked isolation; never execute student code on the host."""
import ast
from copy import deepcopy
import hashlib
import json
import uuid
from unittest.mock import patch

from flask import Flask
import pytest

from test_learner_state import app
from test_tutor_context import headers, formal_body
from test_tutoring_modes import dependencies, Provider
from test_messenger_tutoring import generated
from app.models import db, TrialQuestionProgress
from app.models.learner_state import LearningEvent
from app.models.tutor_context import TutorCodeRun
from app.services.execution_errors import ExecutionInputError, ExecutionUnavailable
from app.services.code_execution import CodeExecutionService
from app.services.python_trace import (POLICY, MAX_STEPS, PythonTraceService, build_program,
                                       decode_report, validate_source, for_tutor)

SOURCE = 'x = 1\nprint(x)'
IMAGE = 'sha256:' + 'a' * 64


def report(source=SOURCE, nonce='test-nonce'):
    return dict(policy=POLICY, nonce=nonce, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        python_version='3.12.10', outcome='completed',
        steps=[{'line':1, 'variables':{'values':{}, 'omitted':0}},
               {'line':2, 'variables':{'values':{'x':'1'}, 'omitted':0}}],
        final_variables={'values':{'x':'1'}, 'omitted':0}, last_line=2,
        stdout='1\n', error_type='', error_message='')


def adapter(language, program, stdin):
    """Read wrapper constants with ast.literal_eval, never evaluate program code."""
    assert language == 'python'
    constants = {}
    for node in ast.parse(program).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in {'SOURCE', 'NONCE'}:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
    return dict(backend='docker', image_id=IMAGE, status={'id':3},
                stdout=json.dumps(report(constants['SOURCE'], constants['NONCE'])))


@pytest.fixture
def trace_app():
    value = Flask(__name__)
    value.config.update(CODE_TRACE_ENABLED=True, CODE_EXECUTION_BACKEND='docker')
    with value.app_context():
        yield value


@pytest.mark.parametrize('source', [
    'import os', 'from sys import version', 'x.__class__', 'eval("1")',
    'x = print\nx(1)', 'def f():\n pass', 'x = [i for i in range(3)]',
    'x = (lambda: 1)()', 'print = 3', '__builtins__', 'print(**{})',
    'try:\n pass\nexcept:\n pass', 'break', '# comment only', 'x = "\ud800"',
    'a = 1\n' * 201, 'x = "' + 'a' * 12000 + '"',
])
def test_subset_rejects_unsupported_or_malformed_source_before_execution(source):
    with pytest.raises(ExecutionInputError):
        validate_source(source)


def test_wrapper_is_parseable_and_preserves_normalized_source():
    source = '结果＝[1, 2]\nfor n in range(2):\n    结果[n] += 1\nprint("全角：＇")'
    normalized, names = validate_source(source)
    assert names == ['n', '结果'] and '结果=' in normalized
    program = build_program(normalized, names, 'nonce')
    compile(program, '<server-wrapper-compilation-only>', 'exec')  # no execution
    assert CodeExecutionService.normalize_python_source(program) == program
    node = next(n for n in ast.parse(program).body if isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'SOURCE')
    assert ast.literal_eval(node.value) == normalized


@pytest.mark.parametrize('field,value', [
    ('nonce','forged'), ('source_sha256','b'*64), ('policy','forged'),
    ('python_version','unknown'), ('outcome',[]), ('steps',[]),
    ('steps',[{'line':True,'variables':{'values':{},'omitted':0}}]),
    ('steps',[{'line':3,'variables':{'values':{},'omitted':0}}]),
    ('final_variables',{'values':{'password':'bad'},'omitted':0}),
    ('final_variables',{'values':{'x':'a'*800},'omitted':0}),
    ('last_line',False), ('stdout','a'*4097), ('error_type','ValueError'),
    ('outcome','step_limit'),
])
def test_reports_fail_closed_on_malformed_or_unbound_evidence(field, value):
    data = report(); data[field] = value
    with pytest.raises(ExecutionUnavailable, match=''):
        decode_report(json.dumps(data), SOURCE, ['x'], 'test-nonce')


@pytest.mark.parametrize('text', ['{}', 'NaN', '\ud800', '{"nonce":1,"nonce":2}',
                                '"\\ud800"', '['*1100 + ']'*1100])
def test_invalid_json_never_becomes_server_error_or_evidence(text):
    with pytest.raises(ExecutionUnavailable):
        decode_report(text, SOURCE, ['x'], 'test-nonce')


def test_report_omits_nonce_and_accepts_partial_bounded_trace():
    data = report(); data.update(outcome='runtime_error', error_type='ZeroDivisionError', error_message='division by zero')
    decoded = decode_report(json.dumps(data), SOURCE, ['x'], 'test-nonce')
    assert decoded['outcome'] == 'runtime_error' and 'nonce' not in decoded
    data.update(outcome='step_limit', error_type='', error_message='', steps=data['steps'] * 40)
    assert len(decode_report(json.dumps(data), SOURCE, ['x'], 'test-nonce')['steps']) == MAX_STEPS


@pytest.mark.parametrize('flag,backend', [(False,'docker'), (True,'judge0'), (True,'disabled')])
def test_no_execution_when_feature_or_isolation_is_unavailable(trace_app, flag, backend):
    trace_app.config.update(CODE_TRACE_ENABLED=flag, CODE_EXECUTION_BACKEND=backend)
    with patch.object(CodeExecutionService, 'run') as execution, pytest.raises(ExecutionUnavailable):
        PythonTraceService.run(SOURCE)
    execution.assert_not_called()


def test_trace_result_is_identified_self_test_not_grade(trace_app):
    with patch.object(CodeExecutionService, 'run', side_effect=adapter) as execution:
        value = PythonTraceService.run(SOURCE, 'input\n')
    assert execution.call_args.args[2] == 'input\n'
    assert value['graded'] is False and value['evidence_scope'] == 'self_test'
    trace = value['trace']
    assert trace['image_id'] == IMAGE and trace['completed'] is True
    assert trace['timing'] == 'variables_before_line' and 'nonce' not in trace
    assert trace['original_code_sha256'] == hashlib.sha256(SOURCE.encode()).hexdigest()


@pytest.mark.parametrize('result', [None, {}, {'backend':'judge0','image_id':IMAGE},
    {'backend':'docker','image_id':'unknown'}, {'backend':'docker','image_id':IMAGE,'status':[]},
    {'backend':'docker','image_id':IMAGE,'status':{'id':True}},
    {'backend':'docker','image_id':IMAGE,'status':{'id':11},'stderr':'private infrastructure error'},
])
def test_unidentified_or_failed_container_never_produces_trace(trace_app, result):
    with patch.object(CodeExecutionService, 'run', return_value=result), pytest.raises(ExecutionUnavailable):
        PythonTraceService.run(SOURCE)


@pytest.mark.parametrize('sid',[5,7,14])
def test_sandbox_limit_has_no_invented_steps(trace_app, sid):
    with patch.object(CodeExecutionService, 'run', return_value={
        'backend':'docker','image_id':IMAGE,'status':{'id':sid},'stdout':'incomplete report'}):
        value = PythonTraceService.run(SOURCE)
    assert value['trace'] is None and value['trace_status'] == 'sandbox_limit' and value['graded'] is False


def test_model_receives_ten_step_excerpt_without_mutating_stored_trace():
    value = {'kind':'trace','result':{'trace':report()}}
    value['result']['trace']['steps'] *= 40
    before = deepcopy(value)
    shortened = for_tutor(value)['result']['trace']
    assert len(shortened['steps']) == 10 and shortened['total_steps'] == 80 and shortened['omitted_steps'] == 70
    assert value == before


def enable(app):
    app.config.update(CODE_TRACE_ENABLED=True, CODE_EXECUTION_BACKEND='docker')


def test_owned_trace_roundtrip_and_no_learning_or_grading_side_effects(app):
    enable(app)
    with patch.object(CodeExecutionService, 'run', side_effect=adapter):
        result = app.test_client().post('/api/v1/code/trace', headers=headers(app), json=formal_body(app, code=SOURCE))
    assert result.status_code == 200
    rid = result.json['data']['run_id']
    with app.app_context():
        row = db.session.get(TutorCodeRun, rid)
        assert row.execution_kind == 'trace' and 'nonce' not in str(row.result)
        assert LearningEvent.query.count() == 0
        assert TrialQuestionProgress.query.filter_by(question_id=app.config['TEST_QUESTION']).one().status == 'pending'
    for changes, expected in [({},200), ({'code':SOURCE+'\n'},409)]:
        response = app.test_client().post('/api/v1/student/tutor/context', headers=headers(app),
            json=formal_body(app, code=SOURCE, run_id=rid) | changes)
        assert response.status_code == expected
    with app.app_context():
        db.session.get(TutorCodeRun, rid).user_id = app.config['TEST_TEACHER']; db.session.commit()
    response = app.test_client().post('/api/v1/student/tutor/context', headers=headers(app),
        json=formal_body(app, code=SOURCE, run_id=rid))
    assert response.status_code == 404


def test_trace_access_feature_input_and_revalidation_fail_without_record(app):
    enable(app); client = app.test_client()
    with patch.object(CodeExecutionService, 'run', side_effect=adapter) as execution:
        assert client.post('/api/v1/code/trace', json={'code':SOURCE}).status_code == 401
        assert client.post('/api/v1/code/trace', headers=headers(app, teacher=True), json={'code':SOURCE}).status_code == 403
        for extra in [{'trace':report()}, {'stdin':[]}, {'language':'java'}, {'code':'x = "\ud800"'}]:
            assert client.post('/api/v1/code/trace', headers=headers(app), json={'code':SOURCE, **extra}).status_code == 400
        execution.assert_not_called()
        app.config['CODE_TRACE_ENABLED'] = False
        assert client.post('/api/v1/code/trace', headers=headers(app), json={'code':SOURCE}).status_code == 503
        execution.assert_not_called()
        app.config['CODE_TRACE_ENABLED'] = True
        with patch('app.services.tutor_context.TutorContextService.current', return_value=False):
            assert client.post('/api/v1/code/trace', headers=headers(app), json={'code':SOURCE}).status_code == 409
    with app.app_context(): assert TutorCodeRun.query.count() == 0


def test_failure_never_saves_runtime_record(app):
    enable(app)
    with patch.object(CodeExecutionService, 'run', side_effect=ExecutionUnavailable('engine_down')):
        response = app.test_client().post('/api/v1/code/trace', headers=headers(app), json={'code':SOURCE})
    assert response.status_code == 503 and response.json['data']['graded'] is False
    with app.app_context(): assert TutorCodeRun.query.count() == 0


def test_tutor_keeps_server_trace_separate_from_model_steps(app, dependencies):
    from app.services.tutoring import TutorService
    enable(app)
    with patch.object(CodeExecutionService, 'run', side_effect=adapter):
        run = app.test_client().post('/api/v1/code/trace', headers=headers(app),
            json=formal_body(app, code=SOURCE)).json['data']
    provider = Provider(generated('algorithm_trace'))
    with app.app_context(), patch('app.services.tutoring.get_llm_provider', return_value=provider):
        response = TutorService.ask(app.config['TEST_STUDENT'], formal_body(app, code=SOURCE,
            run_id=run['run_id'], request_id=str(uuid.uuid4()), mode='algorithm_trace',
            question='请逐行推演这段代码'), automatic=True)
    assert response['execution_trace'] == run['trace']
    assert '模型说明不等同于执行记录' in response['trace_notice']
    assert response['trace_steps'] == generated('algorithm_trace')['trace_steps']
    payload = json.loads(provider.calls[0]['user'])
    assert payload['execution']['result']['trace']['total_steps'] == 2
    assert payload['execution']['evidence_scope'] == 'self_test'
