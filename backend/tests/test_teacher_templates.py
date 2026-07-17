"""Teacher assignment template routes."""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, Trial, TrialQuestion, User, db


class TeacherTemplatesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            teacher_role = Role.query.filter_by(name='teacher').first()
            student_role = Role.query.filter_by(name='student').first()

            self.teacher = User(
                username='template-teacher',
                email='template-teacher@example.com',
                password_hash=generate_password_hash('teacher123'),
                real_name='Template Teacher',
                role_id=teacher_role.id,
            )
            self.student = User(
                username='template-student',
                email='template-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='Template Student',
                role_id=student_role.id,
            )
            db.session.add_all([self.teacher, self.student])
            db.session.flush()

            self.class_obj = Class(
                name='Template Class',
                description='Template publish test class',
                grade_level=3,
                teacher_id=self.teacher.id,
                join_code='TPL001',
            )
            db.session.add(self.class_obj)
            db.session.flush()
            self.student.class_id = self.class_obj.id
            db.session.commit()

            self.class_id = self.class_obj.id
            self.teacher_token = create_access_token(identity=str(self.teacher.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self):
        return {'Authorization': f'Bearer {self.teacher_token}'}

    def test_publish_template_creates_running_trial(self):
        create_resp = self.client.post(
            '/api/v1/teacher/templates',
            json={
                'title': 'Intro template',
                'trial_type': 'solo',
                'knowledge_keys': ['intro'],
                'class_id': self.class_id,
                'duration_minutes': 45,
                'reward_points': 20,
            },
            headers=self.auth(),
        )
        self.assertEqual(create_resp.status_code, 200)
        template_id = create_resp.get_json()['data']['id']

        publish_resp = self.client.post(
            f'/api/v1/teacher/templates/{template_id}/publish',
            json={'class_id': str(self.class_id), 'notify_students': True},
            headers=self.auth(),
        )

        self.assertEqual(publish_resp.status_code, 200)
        data = publish_resp.get_json()['data']
        self.assertEqual(data['student_count'], 1)
        self.assertEqual(data['trial']['class_id'], self.class_id)
        self.assertEqual(data['trial']['status'], 'running')
        self.assertEqual(data['trial']['knowledge_keys'], ['intro'])

        with self.app.app_context():
            trial = Trial.query.filter_by(class_id=self.class_id, title='Intro template').first()
            self.assertIsNotNone(trial)
            self.assertEqual(TrialQuestion.query.filter_by(trial_id=trial.id).count(), 3)


if __name__ == '__main__':
    unittest.main()
