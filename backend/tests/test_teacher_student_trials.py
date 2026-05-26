"""Teacher view student trial history."""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, Trial, TrialParticipation, User, db


class TeacherStudentTrialsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            self.teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='trial-history-student',
                email='trial-history@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='试炼档案学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()
            self.cls = Class(
                name='试炼档案班',
                description='trial history',
                grade_level=2,
                teacher_id=self.teacher.id,
            )
            db.session.add(self.cls)
            db.session.flush()
            self.student.class_id = self.cls.id
            trial = Trial(
                class_id=self.cls.id,
                teacher_id=self.teacher.id,
                title='档案试炼',
                trial_type='solo',
                knowledge_key='dp',
                status='running',
            )
            db.session.add(trial)
            db.session.flush()
            db.session.add(
                TrialParticipation(
                    trial_id=trial.id,
                    user_id=self.student.id,
                    status='completed',
                    score=88,
                )
            )
            db.session.commit()
            self.student_id = self.student.id
            self.teacher_token = create_access_token(identity=str(self.teacher.id))

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_teacher_lists_student_trials(self):
        resp = self.client.get(
            f'/api/v1/teacher/students/{self.student_id}/trials',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()['data']
        self.assertEqual(data['summary']['completed'], 1)
        self.assertEqual(len(data['participations']), 1)


if __name__ == '__main__':
    unittest.main()
