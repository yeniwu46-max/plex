"""Student learning path API tests."""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, Trial, TrialParticipation, User, db


class StudentProgressTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='progress-student',
                email='progress@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='星轨学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()
            cls = Class(name='星轨班', description='p', grade_level=1, teacher_id=teacher.id)
            db.session.add(cls)
            db.session.flush()
            self.student.class_id = cls.id
            trial = Trial(
                class_id=cls.id,
                teacher_id=teacher.id,
                title='DP 试炼',
                trial_type='solo',
                knowledge_key='dp',
                status='ended',
            )
            db.session.add(trial)
            db.session.flush()
            db.session.add(
                TrialParticipation(
                    trial_id=trial.id,
                    user_id=self.student.id,
                    status='completed',
                    score=90,
                )
            )
            db.session.commit()
            self.student_token = create_access_token(identity=str(self.student.id))

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_learning_path_and_archive(self):
        path_resp = self.client.get('/api/v1/student/learning-path', headers=self.auth(self.student_token))
        self.assertEqual(path_resp.status_code, 200)
        domains = path_resp.get_json()['data']['domains']
        self.assertGreaterEqual(len(domains), 1)

        archive_resp = self.client.get('/api/v1/student/archive-insights', headers=self.auth(self.student_token))
        self.assertEqual(archive_resp.status_code, 200)
        self.assertIn('tendency', archive_resp.get_json()['data'])


if __name__ == '__main__':
    unittest.main()
