"""End-to-end contract tests for the student multi-agent code learning cycle."""
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from app import create_app
from app.services.learning_cycle import LearningCycleService


def _timeout_execution(*_args, **_kwargs):
    return {
        'all_passed': False, 'passed_count': 0, 'total': 1, 'submitted_at': '2026-06-26T00:00:00', 'backend': 'mock',
        'results': [{'case_id': 'timeout', 'label': '无限循环检测', 'passed': False, 'expected': '0\n1\n2', 'actual': '',
                     'status': {'id': 5, 'description': 'Time Limit Exceeded'}, 'time': '5.000', 'memory': 4096,
                     'error': 'Execution timed out'}],
    }


def _passed_execution(*_args, **_kwargs):
    return {
        'all_passed': True, 'passed_count': 1, 'total': 1, 'submitted_at': '2026-06-26T00:00:01', 'backend': 'mock',
        'results': [{'case_id': 'fixed', 'label': '修复后测试', 'passed': True, 'expected': '0\n1\n2', 'actual': '0\n1\n2',
                     'status': {'id': 3, 'description': 'Accepted'}, 'time': '0.010', 'memory': 4096, 'error': None}],
    }


def _payload(code: str):
    return {
        'language': 'python', 'code': code, 'run_mode': 'stdout',
        'test_cases': [{'id': 'loop', 'label': '循环', 'expected': '0\n1\n2'}],
        'exerciseId': 'cycle-variable-change', 'questionTitle': '循环变量变化',
        'knowledgePoints': ['循环', 'while 循环'], 'topic': '循环变量变化', 'attemptCount': 1,
        'learningPreference': '我偏好用图解理解变量变化',
    }


def test_timeout_cycle_returns_all_ten_stages_without_external_llm():
    app = create_app('testing')
    with app.app_context(), patch('app.services.learning_cycle.CodeExecutionService.submit', _timeout_execution), \
            patch('app.services.learning_cycle.IflytekSparkService.configured', return_value=False):
        result = LearningCycleService.execute(1, _payload('i = 0\nwhile i < 3:\n    print(i)'))

    assert result['execution']['results'][0]['status']['id'] == 5
    assert result['diagnosis']['errorSubtype'] == 'while_termination'
    assert result['learningProfile']['visualPreferenceConfirmed'] is True
    assert result['learningPath']['nextKnowledgePoint'] == '循环变量变化'
    assert result['resources']['executionDiagram']['steps']
    assert result['resources']['microFix']['answerPolicy']
    assert result['tutor']['mode'] == 'socratic'
    assert result['knowledgeGraphUpdate']['action'] == 'reinforce'
    assert result['learningReport']['outcome'] == 'needs_remediation'
    assert {item['agentId'] for item in result['pipelineTrace']} >= {
        'code_sandbox', 'learning_profile', 'learning_path', 'resource_generation',
        'dialogue_tutor', 'knowledge_graph_update', 'learning_report',
    }


def test_passing_resubmission_updates_graph_and_returns_report():
    app = create_app('testing')
    with app.app_context(), patch('app.services.learning_cycle.CodeExecutionService.submit', _passed_execution), \
            patch('app.services.learning_cycle.IflytekSparkService.configured', return_value=False):
        result = LearningCycleService.execute(1, _payload('i = 0\nwhile i < 3:\n    print(i)\n    i += 1'))
    assert result['execution']['all_passed'] is True
    assert result['knowledgeGraphUpdate']['action'] == 'consolidated'
    assert result['learningReport']['outcome'] == 'passed'


def test_cycle_route_has_a_stable_authenticated_contract():
    app = create_app('testing')
    with app.app_context(), patch('app.services.learning_cycle.CodeExecutionService.submit', _timeout_execution), \
            patch('app.services.learning_cycle.IflytekSparkService.configured', return_value=False):
        token = create_access_token(identity='1')
        response = app.test_client().post(
            '/api/v1/agents/code-learning-cycle', json=_payload('i = 0\nwhile i < 3:\n    print(i)'),
            headers={'Authorization': f'Bearer {token}'},
        )
    assert response.status_code == 200
    data = response.get_json()
    assert data['code'] == 0
    assert data['data']['learningReport']['headline']


def test_route_handles_a_real_mock_sandbox_timeout_without_5xx():
    """Exercise the actual subprocess timeout path, not only a mocked result."""
    app = create_app('testing')
    with app.app_context():
        token = create_access_token(identity='1')
        response = app.test_client().post(
            '/api/v1/agents/code-learning-cycle',
            json=_payload('i = 0\nwhile i < 3:\n    print(i)'),
            headers={'Authorization': f'Bearer {token}'},
        )
    assert response.status_code == 200
    body = response.get_json()['data']
    assert body['execution']['results'][0]['status']['id'] == 5
    assert body['diagnosis']['errorSubtype'] == 'while_termination'
