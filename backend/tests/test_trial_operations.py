"""Trial publish / schedule / end flow."""
import unittest
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, Trial, User, db


class TrialOperationsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            self.teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='trial-ops-student',
                email='trial-ops@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='运营学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()
            self.cls = Class(
                name='试炼运营班',
                description='ops',
                grade_level=2,
                teacher_id=self.teacher.id,
            )
            db.session.add(self.cls)
            db.session.flush()
            self.student.class_id = self.cls.id
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

    def test_draft_publish_and_end(self):
        draft_resp = self.client.post(
            '/api/v1/teacher/trials',
            headers=self.auth(self.teacher_token),
            json={
                'class_id': self.class_id,
                'title': '草稿试炼',
                'trial_type': 'solo',
                'knowledge_key': 'dp',
                'publish_mode': 'draft',
            },
        )
        self.assertEqual(draft_resp.status_code, 200)
        trial_id = draft_resp.get_json()['data']['id']
        self.assertEqual(draft_resp.get_json()['data']['effective_status'], 'draft')

        student_list = self.client.get('/api/v1/student/trials', headers=self.auth(self.student_token))
        self.assertEqual(len(student_list.get_json()['data']['trials']), 0)

        publish_resp = self.client.post(
            f'/api/v1/teacher/trials/{trial_id}/publish',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(publish_resp.status_code, 200)
        self.assertEqual(publish_resp.get_json()['data']['effective_status'], 'running')

        end_resp = self.client.patch(
            f'/api/v1/teacher/trials/{trial_id}',
            headers=self.auth(self.teacher_token),
            json={'status': 'ended'},
        )
        self.assertEqual(end_resp.status_code, 200)
        self.assertEqual(end_resp.get_json()['data']['effective_status'], 'ended')

    def test_scheduled_trial(self):
        starts = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        resp = self.client.post(
            '/api/v1/teacher/trials',
            headers=self.auth(self.teacher_token),
            json={
                'class_id': self.class_id,
                'title': '定时试炼',
                'trial_type': 'team',
                'knowledge_key': 'graph',
                'publish_mode': 'scheduled',
                'starts_at': starts,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['data']['effective_status'], 'scheduled')

        arena = self.client.get('/api/v1/student/trials/arena', headers=self.auth(self.student_token))
        self.assertEqual(arena.status_code, 200)
        self.assertEqual(len(arena.get_json()['data']['trials']), 1)


if __name__ == '__main__':
    unittest.main()
