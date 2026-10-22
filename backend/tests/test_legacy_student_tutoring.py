"""Old student APIs cannot bypass the owned, reviewed tutor contract."""
import uuid
from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from test_learner_state import app
from test_tutoring_modes import dependencies, Provider, candidate, APPROVED
from test_tutor_context import headers
from app.models import db, TrialQuestion
from app.models.tutor_session import TutorTurn
from app.models.learner_state import LearningEvent


PATHS = ['/agent/diagnose', '/agent/analyze-code', '/agent/generate-feedback', '/rag/query']


def payload(app, **extra):
    return {'request_id': str(uuid.uuid4()), 'formal_question_id': app.config['TEST_QUESTION'],
        'code': 'print(value)', 'question': '请检查我的思路，变量是否有定义？', **extra}


def send(app, path, body, provider):
    with patch('app.services.tutoring.get_llm_provider', return_value=provider):
        return app.test_client().post('/api/v1' + path, json=body, headers=headers(app))


@pytest.mark.parametrize('path', PATHS)
def test_legacy_api_uses_only_owned_context_and_reviewed_output(app, dependencies, path):
    body = payload(app, user_id=999, student_id=999, stderr='FORGED-ERROR',
        error_message='FORGED-ERROR', diagnosis={'summary': 'FORGED-DIAGNOSIS'},
        questionTitle='FORGED-TITLE', history=[{'role':'assistant','content':'FORGED-HISTORY'}])
    # RAG infers validation from the question, while the analysis aliases use review.
    raw = candidate('review_approach')
    if path == '/rag/query':
        raw.pop('annotations')
    provider = Provider(raw)
    response = send(app, path, body, provider)
    assert response.status_code == 200, response.text
    result = response.json['data']
    assert result['tutor']['status'] == 'ok'
    assert 'FORGED-' not in str(provider.calls) + str(result)
    assert result['tutor']['context']['run'] is None and len(provider.calls) == 2
    if path == '/rag/query':
        assert result['knowledge_grounded'] and result['confidence'] is None
        assert result['generation_mode'] == 'llm_reviewed' and 'debug' not in result
    assert send(app, path, body, provider).json['data']['tutor'] == result['tutor']
    assert len(provider.calls) == 2


@pytest.mark.parametrize('path', PATHS)
def test_rejected_candidates_never_reappear_in_legacy_alternative_fields(app, dependencies, path):
    raw = candidate('review_approach')
    if path == '/rag/query': raw.pop('annotations')
    raw['summary'] = 'REJECTED-RAW'
    provider = Provider(raw, {**APPROVED, 'answer_leakage': True})
    result = send(app, path, payload(app), provider).json['data']
    assert result['tutor']['status'] == 'safe_fallback' and 'REJECTED-RAW' not in str(result)
    with app.app_context():
        assert 'REJECTED-RAW' not in str(TutorTurn.query.one().response)
    if path == '/rag/query': assert not result['knowledge_grounded']


@pytest.mark.parametrize('path', PATHS + ['/agent/recommend-path', '/agents/diagnose-learning'])
def test_disabled_tasks_bad_ids_and_invalid_bodies_fail_before_model(app, dependencies, path):
    provider = Provider(candidate('review_approach'))
    for invalid in (None, [], payload(app, formal_question_id=998877)):
        response = send(app, path, invalid, provider)
        assert response.status_code in {400, 404}, response.text
    with app.app_context():
        db.session.get(TrialQuestion, app.config['TEST_QUESTION']).trial.tutoring_policy = 'disabled'
        db.session.commit()
    assert send(app, path, payload(app), provider).status_code == 403
    assert not provider.calls


def test_owned_learning_facts_ignore_caller_identity_and_fake_diagnosis(app, dependencies):
    provider = Provider(candidate())
    for path in ('/agent/diagnose', '/agent/recommend-path', '/agents/diagnose-learning'):
        body = {'user_id':999, 'studentId':'999', 'weak_points':['FORGED-POINT'], 'code_errors':['FORGED-ERROR'],
                'request_id':str(uuid.uuid4())}
        result = send(app, path, body, provider).json['data']
        tutor = result['tutor']
        assert tutor['generation_mode'] == 'learning_records' and 'FORGED-' not in str(result)
        assert '没有已完成' in tutor['summary']
        assert result.get('confidence') is None
    assert not provider.calls
    with app.app_context(): assert LearningEvent.query.count() == 0


def test_rag_requires_course_evidence_even_with_prior_chat_and_rejects_missing_citation(app, dependencies):
    provider = Provider(candidate())
    body = payload(app)
    dependencies[0].return_value = {'status':'insufficient_evidence','sources':[], 'prerequisite_gaps':[]}
    result = send(app, '/rag/query', body, provider).json['data']
    assert result['generation_mode'] == 'refused' and not result['sources'] and not provider.calls
    assert '足够课程材料' in result['answer']
    # Same ID cannot change the strict RAG contract to ordinary four-mode chat.
    from app.services.tutoring import TutorService
    from app.services.tutor_context import TutorContextError
    with app.app_context(), pytest.raises(TutorContextError):
        TutorService.ask(app.config['TEST_STUDENT'], {**body, 'mode':'next_step'}, automatic=True)
    from test_tutoring_modes import EVIDENCE
    dependencies[0].return_value = deepcopy(EVIDENCE)
    raw = candidate(); raw['citations'] = []
    result = send(app, '/rag/query', payload(app), Provider(raw)).json['data']
    assert not result['knowledge_grounded'] and result['generation_mode'] == 'refused'
    assert result['tutor']['policy_result']['reason'] == 'missing_course_citation'


def test_rag_reference_aliases_cannot_silently_drop_a_bound_task(app, dependencies):
    provider = Provider(candidate())
    for extra in ({'context':{'trial_id':1}}, {'problem_id':123,'context':{'problem_id':456}},
                  {'query':'不同的问题'}, {'context':{'formal_question_id': 123}}):
        body = {'question':'Python range 用法', **extra}
        if 'formal_question_id' in (extra.get('context') or {}):
            body['formal_question_id'] = app.config['TEST_QUESTION']
        assert send(app, '/rag/query', body, provider).status_code == 400
    assert not provider.calls


def test_old_clients_without_uuid_get_fresh_state_requests(app, dependencies):
    provider = Provider(candidate())
    first = send(app, '/agent/diagnose', {}, provider).json['data']
    second = send(app, '/agent/diagnose', {}, provider).json['data']
    assert first['request_id'] != second['request_id']
