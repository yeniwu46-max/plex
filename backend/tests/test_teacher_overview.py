"""Teacher overview endpoint tests."""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, PointsLog, Role, User, db


class TeacherOverviewTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            teacher_role = Role.query.filter_by(name='teacher').first()
            student_role = Role.query.filter_by(name='student').first()

            self.teacher = User.query.filter_by(username='teacher001').first()
            self.other_teacher = User(
                username='teacher002',
                email='teacher002@example.com',
                password_hash=generate_password_hash('teacher123'),
                real_name='王老师',
                role_id=teacher_role.id,
            )
            self.empty_teacher = User(
                username='teacher-empty',
                email='teacher-empty@example.com',
                password_hash=generate_password_hash('teacher123'),
                real_name='空班教师',
                role_id=teacher_role.id,
            )
            db.session.add_all([self.other_teacher, self.empty_teacher])
            db.session.flush()

            self.own_class = Class(name='A3-教师班', description='测试班级', grade_level=3, teacher_id=self.teacher.id)
            self.other_class = Class(name='A3-他人班', description='越权班级', grade_level=3, teacher_id=self.other_teacher.id)
            db.session.add_all([self.own_class, self.other_class])
            db.session.flush()

            students = [
                User(
                    username='overview-student-1',
                    email='overview1@example.com',
                    password_hash=generate_password_hash('student123'),
                    real_name='学生甲',
                    role_id=student_role.id,
                    class_id=self.own_class.id,
                    total_points=320,
                    level=2,
                ),
                User(
                    username='overview-student-2',
                    email='overview2@example.com',
                    password_hash=generate_password_hash('student123'),
                    real_name='学生乙',
                    role_id=student_role.id,
                    class_id=self.own_class.id,
                    total_points=780,
                    level=3,
                ),
            ]
            db.session.add_all(students)
            self.own_class.student_count = len(students)
            self.other_class.student_count = 0
            db.session.flush()
            db.session.add(PointsLog(user_id=students[1].id, points=50, reason='daily_quest:test'))
            db.session.commit()

            self.own_class_id = self.own_class.id
            self.other_class_id = self.other_class.id
            self.teacher_token = create_access_token(identity=str(self.teacher.id))
            self.empty_teacher_token = create_access_token(identity=str(self.empty_teacher.id))

    def auth_headers(self, token):
        return {'Authorization': f'Bearer {token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_teacher_sees_own_class_with_fallback_ranking(self):
        response = self.client.get('/api/v1/teacher/overview', headers=self.auth_headers(self.teacher_token))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()['data']
        self.assertEqual(payload['selected_class']['id'], self.own_class_id)
        self.assertEqual(payload['metrics']['student_count'], 2)
        self.assertEqual(payload['ranking'][0]['student_name'], '学生乙')
        self.assertEqual(payload['ranking'][0]['points'], 780)

    def test_teacher_cannot_access_other_teacher_class(self):
        response = self.client.get(
            f'/api/v1/teacher/overview?class_id={self.other_class_id}',
            headers=self.auth_headers(self.teacher_token),
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_with_no_classes_gets_empty_payload(self):
        response = self.client.get('/api/v1/teacher/overview', headers=self.auth_headers(self.empty_teacher_token))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()['data']
        self.assertIsNone(payload['selected_class'])
        self.assertEqual(payload['classes'], [])
        self.assertEqual(payload['metrics']['student_count'], 0)


if __name__ == '__main__':
    unittest.main()
