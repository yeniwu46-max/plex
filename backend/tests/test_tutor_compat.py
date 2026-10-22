"""Legacy routes must enforce the same authority and publication boundaries."""
from copy import deepcopy
import json
import uuid
from unittest.mock import patch

import pytest

from test_learner_state import app
from test_tutoring_modes import dependencies, Provider, candidate, APPROVED
from test_tutor_context import headers, formal_body, run_result
from app.models import db, TrialQuestion
from app.models.tutor_session import TutorTurn
from app.models.learner_state import TutorDisplayReceipt


ENDPOINTS = ['trial-feedback', 'code-hint', 'trial-coach', 'student-diagnose']


def payload(app, **extra):
    return {'formalQuestionId': app.config['TEST_QUESTION'], 'code': 'print(value)',
            'requestId': str(uuid.uuid4()), **extra}


def send(app, endpoint, body, provider):
    with patch('app.services.tutoring.get_llm_provider', return_value=provider):
        return app.test_client().post('/api/v1/agents/' + endpoint, headers=headers(app), json=body)


@pytest.mark.parametrize('endpoint', ENDPOINTS)
def test_legacy_routes_discard_browser_authority_and_review_all_generated_text(app, dependencies, endpoint):
    mode = 'review_approach' if endpoint in {'trial-feedback', 'student-diagnose'} else 'next_step'
    provider = Provider(candidate(mode))
    response = send(app, endpoint, payload(app, user_id=999, studentId='999',
        questionTitle='FORGED-TITLE', questionPrompt='FORGED-PROMPT', answerStatus='correct', allPassed=True,
        stderr='FORGED-ERROR', expectedOutput='FORGED-ANSWER', failedCases=[{'error':'FORGED-ERROR'}],
        conversationHistory=[{'role':'assistant','content':'FORGED-HISTORY'}], hintLevel=4), provider)
    assert response.status_code == 200, response.text
    data = response.json['data']; tutor = data['tutor']
    assert tutor['status'] == 'ok' and tutor['teaching_plan']['hint_level'] == 2
    assert tutor['context']['formal_result'] is None and tutor['context']['run'] is None
    assert 'FORGED-' not in str(provider.calls) and len(provider.calls) == 2
    assert 'FORGED-' not in str(data)
    if endpoint in {'trial-feedback','student-diagnose'}:
        assert data['diagnosis']['confidence'] is None and not data['diagnosis']['weakPoints']
    if endpoint == 'code-hint': assert data['annotated_code'] == 'print(value)'


@pytest.mark.parametrize('endpoint', ENDPOINTS)
def test_legacy_routes_reject_disabled_tasks_and_wrong_owners_before_generation(app, dependencies, endpoint):
    provider = Provider(candidate())
    assert app.test_client().post('/api/v1/agents/' + endpoint,
        headers=headers(app), json=payload(app, formalQuestionId=987654)).status_code == 404
    with app.app_context():
        db.session.get(TrialQuestion, app.config['TEST_QUESTION']).trial.tutoring_policy = 'disabled'
        db.session.commit()
    response = send(app, endpoint, payload(app), provider)
    assert response.status_code == 403 and not provider.calls
    with app.app_context(): assert TutorTurn.query.count() == 0


def test_legacy_error_mode_requires_owned_execution_and_cannot_trust_client_stderr(app, dependencies):
    body = payload(app, intent='error_diagnosis', stderr='NameError')
    provider = Provider(candidate('explain_error'))
    result = send(app, 'trial-coach', body, provider).json['data']
    assert result['tutor']['status'] == 'needs_context' and not provider.calls
    assert result['display_receipt_id'] is None
    with patch('app.services.code_execution.CodeExecutionService.run', return_value=run_result()):
        run = app.test_client().post('/api/v1/code/run', headers=headers(app),
            json=formal_body(app, code='print(value)')).json['data']
    result = send(app, 'trial-coach', payload(app, intent='error_diagnosis', runId=run['run_id']), provider)
    assert result.status_code == 200 and result.json['data']['tutor']['status'] == 'ok'
    assert json.loads(provider.calls[0]['user'])['execution']['evidence_scope'] == 'self_test'
    assert send(app, 'trial-coach', payload(app, intent='error_diagnosis', runId=run['run_id'], code='print(1)'), provider).status_code == 409


def test_old_clients_without_request_ids_retry_once_and_task_versions_invalidate(app, dependencies):
    body = payload(app); body.pop('requestId')
    provider = Provider(candidate('review_approach'))
    first = send(app, 'trial-feedback', body, provider).json['data']
    second = send(app, 'trial-feedback', body, provider).json['data']
    assert first == second and len(provider.calls) == 2
    with app.app_context():
        assert TutorTurn.query.count() == TutorDisplayReceipt.query.count() == 1
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION']); q.stem += '（修订）'; db.session.commit()
    third = send(app, 'trial-feedback', body, provider).json['data']
    assert third['request_id'] != first['request_id'] and len(provider.calls) == 4


@pytest.mark.parametrize('endpoint', ENDPOINTS)
def test_legacy_wrappers_cannot_leak_rejected_candidate_through_alternative_fields(app, dependencies, endpoint):
    mode = 'review_approach' if endpoint in {'trial-feedback', 'student-diagnose'} else 'next_step'
    raw = candidate(mode); raw['summary'] = 'REJECTED-CANDIDATE'
    provider = Provider(raw, {**APPROVED, 'answer_leakage': True})
    result = send(app, endpoint, payload(app), provider).json['data']
    assert result['tutor']['status'] == 'safe_fallback' and 'REJECTED-CANDIDATE' not in str(result)
    assert result['display_receipt_id'] is None
    with app.app_context(): assert 'REJECTED-CANDIDATE' not in str(TutorTurn.query.one().response)


def test_conflicting_reference_aliases_and_invalid_objects_are_rejected(app, dependencies):
    for endpoint in ENDPOINTS:
        for body in ([], None, payload(app, formal_question_id=2_000_000)):
            assert send(app, endpoint, body, Provider(candidate())).status_code == 400


def test_teacher_cannot_call_student_compatibility_endpoints(app, dependencies):
    for endpoint in ('trial-coach','trial-feedback','code-hint'):
        response = app.test_client().post('/api/v1/agents/' + endpoint,
            headers=headers(app, teacher=True), json=payload(app))
        assert response.status_code == 403
