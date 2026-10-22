"""Isolation failures and self-test contracts; never execute host Python."""
import json
import os
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from app import create_app
from app.services.code_execution import CodeExecutionService as Runner
from app.services.docker_execution import container_args, run_container
from app.services.execution_errors import ExecutionUnavailable, ExecutionInputError
from app.services.resource_audit.code_tools import run_pytest_if_present, run_runtime_checks


@pytest.fixture
def config():
    app = Flask(__name__)
    app.config.update(CODE_EXECUTION_BACKEND='disabled', JUDGE0_API_URL='')
    with app.app_context():
        yield app.config


def accepted(stdout=''):
    return {'status': {'id': 3, 'description': 'Accepted'}, 'stdout': stdout,
            'stderr': '', 'time': None, 'memory': None, 'backend': 'test_adapter'}


def test_source_normalization_preserves_strings_and_comments():
    assert Runner.normalize_python_source('print（＂Hello!＂）') == 'print("Hello!")'
    assert Runner.normalize_python_source('print("（中文）") # （注释）') == 'print("（中文）") # （注释）'


@pytest.mark.parametrize('backend', ['disabled', 'mock', 'e2b', 'unknown', 'auto'])
def test_unconfigured_or_legacy_runners_never_execute_host(config, backend):
    config['CODE_EXECUTION_BACKEND'] = backend
    with patch('subprocess.Popen') as process, pytest.raises(ExecutionUnavailable):
        Runner.run('python', 'import os; print(os.environ)')
    process.assert_not_called()


@pytest.mark.parametrize('error', [TimeoutError(), ConnectionError(), ValueError('invalid provider json')])
def test_judge_failure_has_no_fallback(config, error):
    config.update(CODE_EXECUTION_BACKEND='judge0', JUDGE0_API_URL='https://judge.invalid')
    with patch.object(Runner, '_judge0_run', side_effect=error), patch('subprocess.Popen') as process:
        with pytest.raises(ExecutionUnavailable):
            Runner.run('python', 'print(1)')
    process.assert_not_called()


@pytest.mark.parametrize('expected,actual,passed', [('', 'unexpected', False), ('', '', True), (0, '0', True), ('x', 'y', False)])
def test_expected_compared_even_when_empty_or_zero(config, expected, actual, passed):
    with patch.object(Runner, 'run', return_value=accepted(actual)):
        result = Runner.submit('python', 'pass', [{'expected': expected}])
    assert result['all_passed'] is passed
    assert result['evidence_scope'] == 'self_test'


@pytest.mark.parametrize('cases', [[], [{}], [None], [{'expected': 'a', 'setup': 5}], [{'expected': ''}] * 31])
def test_invalid_test_sets_rejected_before_running(config, cases):
    with patch.object(Runner, 'run') as runner, pytest.raises(ExecutionInputError):
        Runner.submit('python', 'pass', cases)
    runner.assert_not_called()


def test_failure_halfway_does_not_create_partial_grade(config):
    with patch.object(Runner, 'run', side_effect=[accepted('1'), ExecutionUnavailable()]):
        with pytest.raises(ExecutionUnavailable):
            Runner.submit('python', 'pass', [{'expected': '1'}, {'expected': '2'}])


@pytest.mark.parametrize('language,code,stdin', [('cpp', 'pass', ''), ('python', None, ''), ('python', 'x' * 65537, ''), ('python', 'pass', {})], ids=['language', 'missing-code', 'oversized-code', 'invalid-stdin'])
def test_invalid_code_input(config, language, code, stdin):
    with pytest.raises(ExecutionInputError):
        Runner.run(language, code, stdin)


@pytest.mark.parametrize('status', [1, 2, 13, None])
def test_unfinished_judge_status_is_not_wrong_answer(config, status):
    config.update(CODE_EXECUTION_BACKEND='judge0', JUDGE0_API_URL='https://judge.invalid')
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = [json.dumps({'status': {'id': status}}).encode()]
    with patch('app.services.code_execution.requests.post', return_value=response) as post:
        with pytest.raises(ExecutionUnavailable):
            Runner.run('python', 'pass')
    payload = post.call_args.kwargs['json']
    assert payload['enable_network'] is False
    assert payload['memory_limit'] == 131072 and payload['cpu_time_limit'] == 3


def test_http_unavailability_and_fake_token_contract():
    app = create_app('testing')
    with app.app_context():
        token = create_access_token(identity='1')
        headers = {'Authorization': f'Bearer {token}'}
        client = app.test_client()
        response = client.post('/api/v1/code/run', headers=headers, json={'code': 'print(1)'})
        assert response.status_code == 503
        assert response.json['data']['graded'] is False
        assert response.json['data']['retryable'] is True
        for body in ([], {'code': 123}, {'code': 'pass', 'test_cases': []}):
            assert client.post('/api/v1/code/submit', headers=headers, json=body).status_code == 400
        assert client.get('/api/v1/code/result/invented-token', headers=headers).status_code == 404
        assert client.post('/api/v1/code/run', json={'code': 'pass'}).status_code == 401


def test_docker_sandbox_has_no_network_mounts_or_host_env():
    command = container_args('plex-exec-test', 'plex-python-sandbox:1')
    for flag in ('--network=none', '--read-only', '--cap-drop=ALL',
                 '--security-opt=no-new-privileges', '--user=65534:65534',
                 '--pids-limit=32', '--memory=128m', '--pull=never'):
        assert flag in command
    assert not any(arg in command for arg in ('-v', '--volume', '--mount', '-e', '--env', '--privileged'))


def test_generated_tests_only_execute_in_adapter():
    with patch('app.services.resource_audit.code_tools.CodeExecutionService.run',
               side_effect=ExecutionUnavailable()), patch('subprocess.run') as process:
        result = run_pytest_if_present('def test_untrusted():\n    assert True', '../../outside')
        checks = run_runtime_checks([('candidate', 'print(1)')])
    process.assert_not_called()
    assert result['level'] == checks[0]['level'] == 'FAIL'
    assert 'safety' in result['tool'] and 'safety' in checks[0]['tool']


def test_official_assignment_failure_is_retryable_and_does_not_complete():
    from app.models import db, User, Class, Trial, TrialQuestion, TrialQuestionProgress, StudentMistake
    app = create_app('testing')
    with app.app_context():
        student = User.query.filter_by(username='student001').one()
        teacher = User.query.filter_by(username='teacher001').one()
        cohort = Class(name='执行验收班', teacher_id=teacher.id, grade_level=1)
        db.session.add(cohort)
        db.session.flush()
        student.class_id = cohort.id
        trial = Trial(class_id=student.class_id, teacher_id=teacher.id, title='受控判题',
                      trial_type='solo', knowledge_key='loop', status='running')
        db.session.add(trial)
        db.session.flush()
        question = TrialQuestion(trial_id=trial.id, question_type='coding', stem='输出 1',
                                 options=[], knowledge_key='loop')
        question.set_coding_meta({'test_cases': [{'id': 'server-case', 'expected': '1'}]})
        db.session.add(question)
        db.session.commit()
        question_id = question.id
        token = create_access_token(identity=str(student.id))
        headers = {'Authorization': f'Bearer {token}'}
        client = app.test_client()
        before = StudentMistake.query.filter_by(user_id=student.id).count()
        payload = {'code': 'print(99)', 'test_cases': [{'expected': '99'}], 'all_passed': True}
        response = client.post(f'/api/v1/student/assignments/{question_id}/code-submit',
                               headers=headers, json=payload)
        assert response.status_code == 503 and response.json['data']['graded'] is False
        progress = TrialQuestionProgress.query.filter_by(user_id=student.id, question_id=question_id).first()
        assert progress is None or progress.status == 'pending'
        assert StudentMistake.query.filter_by(user_id=student.id).count() == before
        # Client-supplied expected output cannot replace the stored test suite.
        with patch.object(Runner, 'run', return_value=accepted('99')), \
             patch('app.services.grading_orchestrator.GradingOrchestrator.run_after_submit', return_value=[]):
            result = client.post(f'/api/v1/student/assignments/{question_id}/code-submit',
                                 headers=headers, json=payload)
        assert result.status_code == 200
        assert result.json['data']['code_passed'] is False
        assert result.json['data']['results'][0]['expected'] == '1'


@pytest.mark.skipif(os.getenv('PLEX_TEST_DOCKER') != '1', reason='requires explicitly enabled Docker integration')
def test_real_container_limits_and_audit_runner():
    image = os.getenv('CODE_EXECUTION_DOCKER_IMAGE', 'plex-python-sandbox:1')
    def run(code, stdin=''):
        return run_container(code, stdin, image=image)
    result = run('print(input())', '你好 PLEX\n')
    assert result['status']['id'] == 3 and result['stdout'].strip() == '你好 PLEX'
    assert result['image_id'].startswith('sha256:')
    probe = '''import os, socket
assert os.getuid() == 65534
assert 'PLEX_SANDBOX_CANARY' not in os.environ
assert not os.path.exists('/app/.env')
try:
    open('/cannot_write', 'w').write('x')
except OSError: pass
else: raise AssertionError('root writable')
s = socket.socket(); s.settimeout(1)
assert s.connect_ex(('1.1.1.1', 443)) != 0
print('isolated')
'''
    with patch.dict(os.environ, {'PLEX_SANDBOX_CANARY': 'never-forward'}):
        assert run(probe)['stdout'].strip() == 'isolated'
    assert run('while True: pass')['status']['id'] == 5
    assert run('x = bytearray(256 * 1024 * 1024)')['status']['id'] == 7
    assert run('import time; time.sleep(60)')['status']['id'] == 5
    noisy = run('while True: print("x" * 4096)')
    assert noisy['status']['id'] == 14 and len(noisy['stdout'].encode()) <= 65536
    with patch('app.services.resource_audit.code_tools.CodeExecutionService.run',
               side_effect=lambda _language, code: run(code)):
        assert run_pytest_if_present('def test_add():\n    assert 2+3 == 5', 'test')['level'] == 'PASS'
