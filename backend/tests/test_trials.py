"""Trial API tests."""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, Trial, User, db


class TrialApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            teacher_role = Role.query.filter_by(name='teacher').first()
            student_role = Role.query.filter_by(name='student').first()

            self.teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='trial-student',
                email='trial-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='试炼学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()

            self.cls = Class(
                name='试炼测试班',
                description='trial',
                grade_level=2,
                teacher_id=self.teacher.id,
            )
            db.session.add(self.cls)
            db.session.flush()

            self.student.class_id = self.cls.id
            self.cls.student_count = 1
            db.session.commit()

            self.class_id = self.cls.id
            self.teacher_token = create_access_token(identity=str(self.teacher.id))
            self.student_token = create_access_token(identity=str(self.student.id))

    def auth(self, token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_teacher_create_and_student_complete(self):
        create_resp = self.client.post(
            '/api/v1/teacher/trials',
            headers=self.auth(self.teacher_token),
            json={
                'class_id': self.class_id,
                'title': '单元测试试炼',
                'trial_type': 'solo',
                'knowledge_key': 'dp',
                'difficulty': 70,
                'duration_minutes': 30,
                'reward_points': 25,
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        trial_id = create_resp.get_json()['data']['id']

        list_resp = self.client.get(
            f'/api/v1/teacher/trials?class_id={self.class_id}',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(list_resp.status_code, 200)
        self.assertGreaterEqual(len(list_resp.get_json()['data']['trials']), 1)

        join_resp = self.client.post(
            f'/api/v1/student/trials/{trial_id}/join',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(join_resp.status_code, 200)

        complete_resp = self.client.post(
            f'/api/v1/student/trials/{trial_id}/complete',
            headers=self.auth(self.student_token),
            json={'score': 88},
        )
        self.assertEqual(complete_resp.status_code, 200)
        self.assertEqual(complete_resp.get_json()['data']['participation']['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
