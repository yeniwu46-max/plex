"""统一推荐 API 测试"""
import unittest

from flask_jwt_extended import create_access_token

from app import create_app
from app.models import User, db


class RecommendationApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            self.student = User.query.filter_by(username='student001').first()
            self.student_token = create_access_token(identity=str(self.student.id))

    def auth(self, token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_student_recommendations(self):
        resp = self.client.get(
            '/api/v1/student/recommendations',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body['code'], 0)
        self.assertIn('recommendations', body['data'])
        self.assertIn('weak_knowledge', body['data'])
        self.assertIn('personalized_resources', body['data'])
        self.assertIn('profile_version', body['data'])
        self.assertIn('recommendation_context', body['data'])


if __name__ == '__main__':
    unittest.main()
