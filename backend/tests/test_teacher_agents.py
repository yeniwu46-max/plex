"""教师端智能体接入：班级一键诊断、单生诊断与路径规划。"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, User, db


class TeacherAgentsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            teacher_role = Role.query.filter_by(name='teacher').first()
            student_role = Role.query.filter_by(name='student').first()

            self.teacher = User(
                username='agent-teacher',
                email='agent-teacher@example.com',
                password_hash=generate_password_hash('teacher123'),
                real_name='王老师',
                role_id=teacher_role.id,
            )
            self.other_teacher = User(
                username='agent-teacher-2',
                email='agent-teacher-2@example.com',
                password_hash=generate_password_hash('teacher123'),
                real_name='陈老师',
                role_id=teacher_role.id,
            )
            db.session.add_all([self.teacher, self.other_teacher])
            db.session.flush()

            self.class_obj = Class(
                name='智能体测试班',
                description='教师智能体接入测试',
                grade_level=3,
                teacher_id=self.teacher.id,
                join_code='AGENT1',
            )
            db.session.add(self.class_obj)
            db.session.flush()

            self.student = User(
                username='agent-student',
                email='agent-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='赵同学',
                role_id=student_role.id,
                class_id=self.class_obj.id,
            )
            db.session.add(self.student)
            db.session.commit()

            self.class_id = self.class_obj.id
            self.student_id = self.student.id
            self.teacher_token = create_access_token(identity=str(self.teacher.id))
            self.other_teacher_token = create_access_token(identity=str(self.other_teacher.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self, token: str):
        return {'Authorization': f'Bearer {token}'}

    def test_class_diagnosis_returns_suggestion(self):
        resp = self.client.get(
            f'/api/v1/teacher/class-diagnosis?class_id={self.class_id}',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['classId'], self.class_id)
        self.assertIn('suggestion', data)
        self.assertIn('interventionGroups', data['suggestion'])
        self.assertGreaterEqual(data['studentCount'], 1)

    def test_class_diagnosis_requires_class_id(self):
        resp = self.client.get(
            '/api/v1/teacher/class-diagnosis',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 400)

    def test_class_diagnosis_rejects_foreign_teacher(self):
        resp = self.client.get(
            f'/api/v1/teacher/class-diagnosis?class_id={self.class_id}',
            headers=self.auth(self.other_teacher_token),
        )
        self.assertEqual(resp.status_code, 403)

    def test_student_diagnose(self):
        resp = self.client.post(
            f'/api/v1/teacher/students/{self.student_id}/diagnose',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('diagnosis', resp.get_json()['data'])

    def test_student_plan_path(self):
        resp = self.client.post(
            f'/api/v1/teacher/students/{self.student_id}/plan-path',
            json={},
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 200)

    def test_student_diagnose_rejects_foreign_teacher(self):
        resp = self.client.post(
            f'/api/v1/teacher/students/{self.student_id}/diagnose',
            headers=self.auth(self.other_teacher_token),
        )
        self.assertEqual(resp.status_code, 403)


if __name__ == '__main__':
    unittest.main()
