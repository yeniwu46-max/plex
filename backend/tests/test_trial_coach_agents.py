"""试炼编程页辅导智能体接口测试。"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Role, User, db


class TrialCoachAgentsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            self.student = User(
                username='trial-coach-student',
                email='trial-coach-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='试炼学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.commit()
            self.token = create_access_token(identity=str(self.student.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self):
        return {'Authorization': f'Bearer {self.token}'}

    def _payload(self, intent: str):
        return {
            'intent': intent,
            'exerciseId': 'stage1-intro-greet',
            'questionTitle': '星际问候',
            'questionPrompt': '使用 print 输出 Hello, PLEX!',
            'topic': 'print 与字符串',
            'code': 'print("Hello")',
            'stderr': '',
            'stdout': 'Hello',
            'expectedOutput': 'Hello, PLEX!',
            'failedCases': [{
                'label': '样例 1',
                'expected': 'Hello, PLEX!',
                'actual': 'Hello',
            }],
            'caseResults': [{'passed': False}],
            'allPassed': False,
            'answerStatus': 'wrong',
        }

    def test_error_diagnosis_returns_guidance_not_answer(self):
        resp = self.client.post('/api/v1/agents/trial-coach', json=self._payload('error_diagnosis'), headers=self.auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['agentId'], 'trial_error_diagnosis')
        self.assertEqual(data['policy'], 'no_direct_answer')
        self.assertTrue(data['response'])
        self.assertNotIn('Hello, PLEX!', data['response'])

    def test_code_quality_intent(self):
        resp = self.client.post('/api/v1/agents/trial-coach', json=self._payload('code_quality'), headers=self.auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['agentId'], 'trial_code_quality')
        self.assertIn('improvements', data)

    def test_optimization_intent(self):
        resp = self.client.post('/api/v1/agents/trial-coach', json=self._payload('optimization'), headers=self.auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['agentId'], 'trial_optimization')

    def test_invalid_intent_rejected(self):
        resp = self.client.post(
            '/api/v1/agents/trial-coach',
            json={**self._payload('error_diagnosis'), 'intent': 'give_answer'},
            headers=self.auth(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_custom_question_with_user_message(self):
        payload = {
            **self._payload('custom'),
            'intent': 'custom',
            'userQuestion': '我的输出为什么少了一个逗号？',
        }
        resp = self.client.post('/api/v1/agents/trial-coach', json=payload, headers=self.auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['agentId'], 'trial_custom_coach')
        self.assertTrue(data['response'])


if __name__ == '__main__':
    unittest.main()
