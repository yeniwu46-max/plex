"""学习评估报告 API 测试"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, Trial, TrialParticipation, User, db


class EvaluationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='eval-student',
                email='eval@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='评估学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()
            cls = Class(name='评估班', description='e', grade_level=1, teacher_id=teacher.id)
            db.session.add(cls)
            db.session.flush()
            self.student.class_id = cls.id
            self.class_id = cls.id
            trial = Trial(
                class_id=cls.id,
                teacher_id=teacher.id,
                title='评估试炼',
                trial_type='solo',
                knowledge_key='algo',
                status='ended',
            )
            db.session.add(trial)
            db.session.flush()
            db.session.add(
                TrialParticipation(
                    trial_id=trial.id,
                    user_id=self.student.id,
                    status='completed',
                    score=80,
                )
            )
            db.session.commit()
            self.student_token = create_access_token(identity=str(self.student.id))
            self.teacher_token = create_access_token(identity=str(teacher.id))

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_student_learning_report(self):
        resp = self.client.get(
            '/api/v1/student/learning-report?period=7d',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()['data']
        self.assertIn('summary', body)
        self.assertIn('domain_mastery', body)
        self.assertIn('recommendations', body)

    def test_teacher_class_evaluation(self):
        resp = self.client.get(
            f'/api/v1/teacher/class-evaluation?class_id={self.class_id}&period=7d',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()['data']
        self.assertEqual(body['class_id'], self.class_id)
        self.assertIn('students', body)


if __name__ == '__main__':
    unittest.main()
