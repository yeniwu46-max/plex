"""Legacy trial feedback keeps its public shape without accepting a browser verdict."""
from unittest.mock import patch
from test_learner_state import app
from test_tutor_context import headers


def test_trial_feedback_route_returns_diagnosis(app):
    with patch('app.services.tutoring.KnowledgeService.tutor_evidence', return_value={
            'status':'insufficient_evidence','sources':[], 'prerequisite_gaps':[]}):
        response = app.test_client().post('/api/v1/agents/trial-feedback', headers=headers(app),
            json={'formalQuestionId':app.config['TEST_QUESTION'], 'code':'print(1)', 'answerStatus':'correct'})
    assert response.status_code == 200, response.text
    data = response.json['data']
    assert data['feedback']['shortFeedback'] and data['tutor']['status'] == 'safe_fallback'
    assert data['diagnosis']['confidence'] is None
    assert data['context']['formal_result'] is None


def test_trial_feedback_requires_code(app):
    response = app.test_client().post('/api/v1/agents/trial-feedback', headers=headers(app), json={})
    assert response.status_code == 400
