import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from app import create_app
from app.models import StudentProfile, StudentProfileHistory, User, db


class StudentProfileApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student = User.query.filter_by(username='student001').first()
            self.token = create_access_token(identity=str(student.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self):
        return {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}

    def test_profile_chat_and_manual_update(self):
        response = self.client.post(
            '/api/v1/student/profile/chat',
            headers=self.auth(),
            json={
                'message': '我是计算机专业大一学生，零基础，希望两周学会Python。'
                           '我喜欢代码案例和分步讲解，每天学习30分钟，兴趣是数据处理，循环边界容易错。',
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()['data']
        self.assertIn(data['backend'], ('local_rules', 'spark'))
        self.assertGreaterEqual(len(data['proposed_changes']), 7)
        self.assertEqual(data['profile']['completion_rate'], 100)

        update = self.client.put(
            '/api/v1/student/profile',
            headers=self.auth(),
            json={'changes': {'explanation_preference': '先给代码，再解释概念'}},
        )
        self.assertEqual(update.status_code, 200)
        dimension = update.get_json()['data']['dimensions']['explanation_preference']
        self.assertEqual(dimension['source'], 'confirmed')

        history = self.client.get('/api/v1/student/profile/history', headers=self.auth())
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(history.get_json()['data']['total'], 2)

    def test_empty_profile_shape(self):
        response = self.client.get('/api/v1/student/profile', headers=self.auth())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()['data']
        self.assertEqual(data['completion_rate'], 0)
        self.assertEqual(len(data['dimensions']), 8)
        with self.app.app_context():
            self.assertEqual(StudentProfile.query.count(), 0)

    def test_diagnostic_can_skip_or_record_twelve_answers(self):
        diagnostic = self.client.get('/api/v1/student/profile/diagnostic', headers=self.auth())
        self.assertEqual(diagnostic.status_code, 200)
        questions = diagnostic.get_json()['data']['questions']
        self.assertEqual(len(questions), 12)
        answers = {item['id']: item['correct_index'] for item in questions}
        completed = self.client.post('/api/v1/student/profile/diagnostic', headers=self.auth(), json={'answers': answers})
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.get_json()['data']['diagnostic']['status'], 'completed')

    def test_recalibration_requires_real_api_before_profile_update(self):
        model_changes = {
            'explanation_preference': {
                'value': '代码示例优先并配合分步讲解',
                'confidence': 0.94,
                'evidence': ['学生明确选择代码示例优先'],
                'source': 'mixed',
            },
        }
        with patch(
            'agents.learning_profile_agent.LearningProfileAgent.recalibrate',
            return_value=(model_changes, 'llm'),
        ) as recalibrate:
            response = self.client.post(
                '/api/v1/student/profile/recalibrate',
                headers=self.auth(),
                json={'changes': {'explanation_preference': '代码示例优先'}},
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()['data']
        self.assertEqual(data['backend'], 'llm')
        self.assertEqual(
            data['profile']['dimensions']['explanation_preference']['value'],
            '代码示例优先并配合分步讲解',
        )
        recalibrate.assert_called_once()
        with self.app.app_context():
            history = StudentProfileHistory.query.order_by(StudentProfileHistory.id.desc()).first()
            self.assertEqual(history.reason, 'ai_recalibration')
            self.assertEqual(history.backend, 'llm_api')

    def test_recalibration_api_failure_does_not_write_profile(self):
        with patch(
            'agents.learning_profile_agent.LearningProfileAgent.recalibrate',
            return_value=({}, 'local_rules'),
        ):
            response = self.client.post(
                '/api/v1/student/profile/recalibrate',
                headers=self.auth(),
                json={'changes': {'learning_pace': '每天 25 分钟专注练习'}},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn('未保存任何修改', response.get_json()['message'])
        with self.app.app_context():
            self.assertEqual(StudentProfile.query.count(), 0)
            self.assertEqual(StudentProfileHistory.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
