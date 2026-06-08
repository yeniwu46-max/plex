import unittest

from flask_jwt_extended import create_access_token

from app import create_app
from app.models import StudentProfile, User, db


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
        self.assertEqual(data['backend'], 'local_rules')
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
        self.assertEqual(len(data['dimensions']), 7)
        with self.app.app_context():
            self.assertEqual(StudentProfile.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
