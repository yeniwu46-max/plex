"""Legacy execution cycle shares the tutor claim, context and publication gates."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import uuid
from unittest.mock import patch

import pytest

from test_learner_state import app
from test_tutoring_modes import dependencies, Provider, candidate, APPROVED
from test_tutor_context import headers
from app.models import db, TrialQuestion
from app.models.learner_state import LearningEvent, TutorDisplayReceipt
from app.models.tutor_context import TutorCodeRun
from app.models.tutor_session import TutorTurn
from app.services.execution_errors import ExecutionUnavailable


def execution(passed=False):
    return {'all_passed':passed, 'passed_count':int(passed), 'total':1, 'backend':'test-sandbox',
        'submitted_at':'2026-10-16T00:00:00', 'results':[{'case_id':'case-1', 'label':'自测',
        'passed':passed, 'expected':'3', 'actual':'3' if passed else '',
        'status':{'id':3 if passed else 5,'description':'Accepted' if passed else 'Time Limit Exceeded'},
        'error':None if passed else 'Execution timed out', 'time':'0.1','memory':1024}]}


def payload(app, **extra):
    return {'request_id':str(uuid.uuid4()), 'formal_question_id':app.config['TEST_QUESTION'],
        'code':'print(value)', 'language':'python', 'test_cases':[{'id':'case-1','expected':'3'}], **extra}


def send(app, body):
    return app.test_client().post('/api/v1/agents/code-learning-cycle', json=body, headers=headers(app))


@pytest.mark.parametrize('passed', [False, True])
def test_cycle_uses_actual_self_test_and_reviewed_help_without_fixed_loop_material(app, dependencies, passed):
    provider = Provider(candidate('review_approach'))
    body = payload(app, learningPreference='FORGED-PREFERENCE', knowledgePoints=['FORGED-KNOWLEDGE'],
        stderr='FORGED-ERROR', questionTitle='FORGED-TITLE')
    with patch('app.services.learning_cycle.CodeExecutionService.submit', return_value=execution(passed)) as run, \
         patch('app.services.tutoring.get_llm_provider', return_value=provider):
        first = send(app, body)
        assert first.status_code == 200, first.text
        data = first.json['data']
        assert data['execution']['all_passed'] == passed
        assert data['execution']['evidence_scope'] == 'self_test'
        assert data['tutorResponse']['status'] == 'ok'
        assert data['resources']['executionDiagram'] is data['resources']['microFix'] is None
        assert data['knowledgeGraphUpdate']['action'] == 'unchanged'
        assert not data['learningProfile']['visualPreferenceConfirmed']
        assert 'FORGED-' not in str(provider.calls) + str(data)
        assert data['tutorResponse']['context']['run']['id'] == data['execution']['run_id']
        assert send(app, body).json['data'] == data
        assert run.call_count == 1 and len(provider.calls) == 2
        assert send(app, {**body, 'test_cases':[{'expected':'different'}]}).status_code == 409
        assert run.call_count == 1
    with app.app_context():
        assert TutorCodeRun.query.count() == TutorTurn.query.count() == 1
        assert LearningEvent.query.count() == 0
        assert TutorDisplayReceipt.query.count() == 1


def test_cycle_rejects_teacher_disabled_or_foreign_task_before_execution(app, dependencies):
    with patch('app.services.learning_cycle.CodeExecutionService.submit') as run:
        assert send(app, payload(app, formal_question_id=9876543)).status_code == 404
        with app.app_context():
            db.session.get(TrialQuestion, app.config['TEST_QUESTION']).trial.tutoring_policy = 'disabled'
            db.session.commit()
        assert send(app, payload(app)).status_code == 403
        assert not run.called
        response = app.test_client().post('/api/v1/agents/code-learning-cycle', json=payload(app),
            headers=headers(app, app.config['TEST_TEACHER']))
        assert response.status_code == 403


def test_cycle_executor_unavailable_is_retryable_without_grade_or_model(app, dependencies):
    body = payload(app)
    provider = Provider(candidate('review_approach'))
    with patch('app.services.learning_cycle.CodeExecutionService.submit', side_effect=ExecutionUnavailable('busy')), \
         patch('app.services.tutoring.get_llm_provider', return_value=provider):
        response = send(app, body)
        assert response.status_code == 503
        assert response.json['data']['retryable'] and not response.json['data']['graded']
        assert not provider.calls
    with app.app_context():
        assert TutorCodeRun.query.count() == LearningEvent.query.count() == TutorDisplayReceipt.query.count() == 0
        assert TutorTurn.query.one().status == 'failed'
    with patch('app.services.learning_cycle.CodeExecutionService.submit', return_value=execution()), \
         patch('app.services.tutoring.get_llm_provider', return_value=provider):
        assert send(app, body).status_code == 200


def test_cycle_rechecks_withdrawal_during_execution_before_any_model(app, dependencies):
    def withdraw(*args, **kwargs):
        row = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        row.trial.tutoring_policy = 'disabled'
        db.session.commit()
        return execution()
    provider = Provider(candidate('review_approach'))
    with patch('app.services.learning_cycle.CodeExecutionService.submit', side_effect=withdraw), \
         patch('app.services.tutoring.get_llm_provider', return_value=provider):
        assert send(app, payload(app)).status_code == 409
        assert not provider.calls
    with app.app_context(): assert TutorTurn.query.one().status == 'failed'


def test_cycle_rejected_model_preserves_execution_and_drops_all_candidate_text(app, dependencies):
    raw = candidate('review_approach'); raw['summary'] = 'REJECTED-RAW'
    provider = Provider(raw, {**APPROVED, 'answer_leakage':True})
    with patch('app.services.learning_cycle.CodeExecutionService.submit', return_value=execution(True)), \
         patch('app.services.tutoring.get_llm_provider', return_value=provider):
        data = send(app, payload(app)).json['data']
    assert data['execution']['all_passed']
    assert data['tutorResponse']['status'] == 'safe_fallback'
    assert not data['display_receipt_id'] and 'REJECTED-RAW' not in str(data)


def test_cycle_concurrent_retry_does_not_execute_twice(app, dependencies):
    entered, finish = Event(), Event()
    def slow(*args, **kwargs):
        entered.set()
        assert finish.wait(10)
        return execution()
    body = payload(app)
    with patch('app.services.learning_cycle.CodeExecutionService.submit', side_effect=slow) as run, \
         patch('app.services.tutoring.get_llm_provider', return_value=Provider(candidate('review_approach'))), \
         ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(send, app, body)
        try:
            assert entered.wait(10)
            assert send(app, body).status_code == 409
            assert run.call_count == 1
        finally:
            finish.set()
        assert first.result(timeout=10).status_code == 200


def test_cycle_invalid_inputs_never_claim_or_execute(app, dependencies):
    with patch('app.services.learning_cycle.CodeExecutionService.submit') as run:
        for body in ([], None, payload(app, test_cases=[]), payload(app, test_cases=[{}]),
                     payload(app, code=''), payload(app, run_mode=[]), payload(app, run_mode={})):
            assert send(app, body).status_code == 400
        assert not run.called
    with app.app_context(): assert TutorTurn.query.count() == 0
