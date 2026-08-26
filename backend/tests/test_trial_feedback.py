"""试炼页按需小E 反馈端点。"""
from unittest.mock import patch

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Role, User, db


def test_trial_feedback_route_returns_diagnosis():
    app = create_app('testing')
    with app.app_context():
        student_role = Role.query.filter_by(name='student').first()
        student = User(
            username='trial-feedback-student',
            email='trial-feedback@example.com',
            password_hash=generate_password_hash('student123'),
            real_name='反馈同学',
            role_id=student_role.id,
        )
        db.session.add(student)
        db.session.commit()
        token = create_access_token(identity=str(student.id))

        payload = {
            'exerciseId': 'hello-print',
            'code': 'print("Hello, PLEX!")',
            'knowledgePoints': ['intro'],
            'attemptCount': 1,
            'answerStatus': 'correct',
            'questionTitle': '星际问候',
        }
        with (
            patch('app.services.agent_orchestrator.IflytekSparkService.configured', return_value=False),
            patch('app.services.learning_path.LearningPathService._bind_resources') as bind_resources,
            patch('app.services.learning_path.LearningPathService._bind_trials') as bind_trials,
        ):
            response = app.test_client().post(
                '/api/v1/agents/trial-feedback',
                json=payload,
                headers={'Authorization': f'Bearer {token}'},
            )

    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body['code'] == 0
    assert 'diagnosis' in body['data']
    assert body['data']['feedback']['shortFeedback']
    assert '符合预期' in body['data']['codeAnalysis']['codeIssueSummary']
    bind_resources.assert_not_called()
    bind_trials.assert_not_called()


def test_trial_feedback_requires_code():
    app = create_app('testing')
    with app.app_context():
        token = create_access_token(identity='1')
        response = app.test_client().post(
            '/api/v1/agents/trial-feedback',
            json={'exerciseId': 'hello-print'},
            headers={'Authorization': f'Bearer {token}'},
        )
    assert response.status_code == 400
