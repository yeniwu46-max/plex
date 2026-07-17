"""学生入班申请与教师审核。"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, User, db


class ClassEnrollmentTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            teacher_role = Role.query.filter_by(name='teacher').first()
            student_role = Role.query.filter_by(name='student').first()

            self.teacher = User(
                username='enroll-teacher',
                email='enroll-teacher@example.com',
                password_hash=generate_password_hash('teacher123'),
                real_name='李老师',
                role_id=teacher_role.id,
            )
            self.student = User(
                username='enroll-student',
                email='enroll-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='张同学',
                role_id=student_role.id,
            )
            db.session.add_all([self.teacher, self.student])
            db.session.flush()

            self.class_obj = Class(
                name='测试探索班',
                description='入班申请测试',
                grade_level=3,
                teacher_id=self.teacher.id,
                join_code='ABC123',
            )
            db.session.add(self.class_obj)
            db.session.commit()
            self.class_id = self.class_obj.id

            self.teacher_token = create_access_token(identity=str(self.teacher.id))
            self.student_token = create_access_token(identity=str(self.student.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self, token: str):
        return {'Authorization': f'Bearer {token}'}

    def test_student_apply_and_teacher_approve(self):
        lookup = self.client.post(
            '/api/v1/class-enrollments/lookup',
            json={'join_code': 'abc123'},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(lookup.status_code, 200)
        self.assertEqual(lookup.get_json()['data']['class_name'], '测试探索班')

        apply_resp = self.client.post(
            '/api/v1/class-enrollments/apply',
            json={'join_code': 'ABC123', 'message': '希望加入班级'},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(apply_resp.status_code, 201)
        request_id = apply_resp.get_json()['data']['id']

        duplicate = self.client.post(
            '/api/v1/class-enrollments/apply',
            json={'join_code': 'ABC123'},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(duplicate.status_code, 400)

        pending = self.client.get(
            '/api/v1/class-enrollments?status=pending',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(len(pending.get_json()['data']), 1)

        review = self.client.post(
            f'/api/v1/class-enrollments/{request_id}/review',
            json={'approve': True, 'note': '欢迎加入'},
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(review.status_code, 200)

        with self.app.app_context():
            student = db.session.get(User, self.student.id)
            self.assertEqual(student.class_id, self.class_id)

    def test_teacher_reject_enrollment(self):
        apply_resp = self.client.post(
            '/api/v1/class-enrollments/apply',
            json={'join_code': 'ABC123'},
            headers=self.auth(self.student_token),
        )
        request_id = apply_resp.get_json()['data']['id']

        review = self.client.post(
            f'/api/v1/class-enrollments/{request_id}/review',
            json={'approve': False, 'note': '班级已满'},
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(review.status_code, 200)
        self.assertEqual(review.get_json()['data']['status'], 'rejected')

        with self.app.app_context():
            student = db.session.get(User, self.student.id)
            self.assertIsNone(student.class_id)


if __name__ == '__main__':
    unittest.main()
