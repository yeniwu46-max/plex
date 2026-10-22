"""Stats drill-down uses full, owned participation history, never a recent slice."""
from datetime import timedelta
from flask_jwt_extended import create_access_token
import pytest
from test_learner_state import app
from test_tutor_context import headers
from app.models import db, Trial, TrialParticipation, User
from app.utils.time import utc_now


def seed_history(app):
    student = db.session.get(User, app.config['TEST_STUDENT'])
    other = User(username='stat_other', email='stats@example.test', password_hash='unused', role_id=student.role_id)
    db.session.add(other); db.session.flush()
    other_id = other.id
    for i in range(15):
        trial = Trial(class_id=student.class_id, teacher_id=app.config['TEST_TEACHER'],
                      title='内部通关试炼' if i == 14 else f'真实试炼 {i}',
                      reward_points=0 if i == 14 else 35, status='running')
        db.session.add(trial); db.session.flush()
        db.session.add(TrialParticipation(trial_id=trial.id, user_id=student.id,
            status='completed' if i < 12 or i == 14 else 'joined' if i == 12 else 'abandoned',
            score=i * 5 if i < 12 else 100,
            joined_at=utc_now() - timedelta(days=i), completed_at=utc_now() if i < 12 else None))
        db.session.add(TrialParticipation(trial_id=trial.id, user_id=other_id, status='completed', score=99))
    db.session.commit()
    return other_id


def test_records_match_full_totals_and_hide_other_students(app):
    with app.app_context():
        other_id = seed_history(app)
    client = app.test_client(); auth = headers(app)
    summary = client.get('/api/v1/student/trial-stats', headers=auth).json['data']['summary']
    assert summary == {'total_participations': 14, 'completed_count': 12, 'active_count': 1, 'avg_score': 28}
    endpoint = '/api/v1/student/trial-stats/records'
    first = client.get(endpoint + '?status=completed&page=1', headers=auth).json['data']
    second = client.get(endpoint + '?status=completed&page=2', headers=auth).json['data']
    assert first['total'] == 12 and len(first['items']) == 10 and len(second['items']) == 2
    assert not ({r['id'] for r in first['items']} & {r['id'] for r in second['items']})
    assert all(r['score'] != 99 and 'user_id' not in r and 'questions' not in r for r in first['items'])
    active = client.get(endpoint + '?status=active', headers=auth).json['data']
    assert active['total'] == 1 and active['items'][0]['score'] is None
    all_rows = client.get(endpoint + f'?status=all&page_size=50&user_id={other_id}', headers=auth).json['data']
    assert all_rows['total'] == 14 and len(all_rows['items']) == 14
    assert all('内部' not in r['title'] for r in all_rows['items'])
    assert client.get(endpoint + '?page=99', headers=auth).json['data']['items'] == []


@pytest.mark.parametrize('query', ['status=unknown', 'page=0', 'page=1.5', 'page=abc', 'page_size=0', 'page_size=51'])
def test_invalid_filters_are_rejected(app, query):
    response = app.test_client().get('/api/v1/student/trial-stats/records?' + query, headers=headers(app))
    assert response.status_code == 400 and response.json['code'] == 40001


def test_auth_roles_and_empty_history(app):
    client = app.test_client(); endpoint = '/api/v1/student/trial-stats/records'
    assert client.get(endpoint).status_code == 401
    assert client.get(endpoint, headers=headers(app, teacher=True)).status_code == 403
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if admin:
            token = create_access_token(identity=str(admin.id))
            assert client.get(endpoint, headers={'Authorization': 'Bearer ' + token}).status_code == 403
    response = client.get(endpoint, headers=headers(app))
    assert response.status_code == 200
    assert response.json['data'] == {'items': [], 'total': 0, 'page': 1, 'page_size': 10}
