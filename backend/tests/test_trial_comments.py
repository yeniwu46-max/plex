"""试炼题目评论。"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Role, User, db


class TrialCommentsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            self.student = User(
                username='comment-student',
                email='comment-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='评论同学',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.commit()
            self.student_token = create_access_token(identity=str(self.student.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self, token: str):
        return {'Authorization': f'Bearer {token}'}

    def test_create_reply_and_like(self):
        create_resp = self.client.post(
            '/api/v1/trial-comments',
            json={'question_ref': 'py-loop-01', 'content': '这题循环边界有点绕'},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(create_resp.status_code, 201)
        comment_id = create_resp.get_json()['data']['id']
        self.assertIn('author_avatar_url', create_resp.get_json()['data'])

        reply_resp = self.client.post(
            '/api/v1/trial-comments',
            json={'question_ref': 'py-loop-01', 'content': '我也卡在这里', 'parent_id': comment_id},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(reply_resp.status_code, 201)

        list_resp = self.client.get(
            '/api/v1/trial-comments?question_ref=py-loop-01',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(list_resp.status_code, 200)
        items = list_resp.get_json()['data']['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(len(items[0]['replies']), 1)

        like_resp = self.client.post(
            f'/api/v1/trial-comments/{comment_id}/like',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(like_resp.status_code, 200)
        self.assertTrue(like_resp.get_json()['data']['liked'])
        self.assertEqual(like_resp.get_json()['data']['like_count'], 1)

        unlike_resp = self.client.post(
            f'/api/v1/trial-comments/{comment_id}/like',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(unlike_resp.status_code, 200)
        self.assertFalse(unlike_resp.get_json()['data']['liked'])
        self.assertEqual(unlike_resp.get_json()['data']['like_count'], 0)
