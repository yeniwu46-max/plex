"""边界条件补给站紧急任务"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import EmergencyMissionSession, Role, User, db


class EmergencyMissionTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            self.student = User(
                username='emergency-student',
                email='emergency@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='紧急学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.commit()
            self.token = create_access_token(identity=str(self.student.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth(self):
        return {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}

    def test_start_submit_and_archive(self):
        start = self.client.post('/api/v1/student/emergency-missions/start', headers=self.auth())
        self.assertEqual(start.status_code, 200)
        session = start.get_json()['data']
        self.assertEqual(len(session['questions']), 3)

        answers = [
            {'question_id': q['id'], 'selected_index': q.get('correct_index', 0)}
            for q in session['questions']
        ]
        # 提交前不返回答案
        self.assertNotIn('correct_index', session['questions'][0])

        submit = self.client.post(
            f"/api/v1/student/emergency-missions/{session['id']}/submit",
            headers=self.auth(),
            json={'answers': [{'question_id': q['id'], 'selected_index': 0} for q in session['questions']]},
        )
        self.assertEqual(submit.status_code, 200)
        body = submit.get_json()['data']
        self.assertIn('correct_index', body['session']['questions'][0])

        archive = self.client.get('/api/v1/student/archive-insights', headers=self.auth())
        self.assertEqual(archive.status_code, 200)
        records = archive.get_json()['data']['emergency_missions']
        self.assertGreaterEqual(len(records), 1)

        with self.app.app_context():
            self.assertEqual(EmergencyMissionSession.query.count(), 1)


if __name__ == '__main__':
    unittest.main()
