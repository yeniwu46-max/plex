"""教师试炼题目下发到学生端"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, TrialQuestion, User, db


class AssignmentApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            self.teacher = User.query.filter_by(username='teacher001').first()

            self.student = User(
                username='assign-student',
                email='assign-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='布置学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()

            self.cls = Class(
                name='布置测试班',
                description='assignment',
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

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self, token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def test_publish_trial_generates_questions_for_student(self):
        create_resp = self.client.post(
            '/api/v1/teacher/trials',
            headers=self.auth(self.teacher_token),
            json={
                'class_id': self.class_id,
                'title': '动态规划小测',
                'knowledge_key': 'dp',
                'publish_mode': 'now',
            },
        )
        self.assertEqual(create_resp.status_code, 200)

        list_resp = self.client.get(
            '/api/v1/student/assignments',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(list_resp.status_code, 200)
        body = list_resp.get_json()['data']
        self.assertGreaterEqual(body['pending_count'], 1)
        self.assertGreaterEqual(len(body['items']), 1)
        question = body['items'][0]
        self.assertIn('stem', question)
        self.assertGreaterEqual(len(question['options']), 2)

        answer_resp = self.client.post(
            f"/api/v1/student/assignments/{question['id']}/answer",
            headers=self.auth(self.student_token),
            json={'selected_index': 0},
        )
        self.assertEqual(answer_resp.status_code, 200)
        result = answer_resp.get_json()['data']
        self.assertIn('correct', result)

        with self.app.app_context():
            count = TrialQuestion.query.count()
            self.assertGreaterEqual(count, 3)


if __name__ == '__main__':
    unittest.main()
