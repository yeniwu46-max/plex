"""错题本 API 测试"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, StudentMistake, Trial, TrialQuestion, User, db
from app.services.question_generator import QuestionGenerator


class MistakesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            teacher_role = Role.query.filter_by(name='teacher').first()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student = User(
                username='mistake-student',
                email='mistake@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='错题学生',
                role_id=student_role.id,
            )
            db.session.add(self.student)
            db.session.flush()
            cls = Class(name='错题班', description='t', grade_level=1, teacher_id=teacher.id)
            db.session.add(cls)
            db.session.flush()
            self.student.class_id = cls.id
            self.class_id = cls.id
            trial = Trial(
                class_id=cls.id,
                teacher_id=teacher.id,
                title='测试试炼',
                trial_type='solo',
                knowledge_key='dp',
                status='running',
            )
            db.session.add(trial)
            db.session.flush()
            self.trial_id = trial.id
            QuestionGenerator.ensure_for_trial(trial)
            question = TrialQuestion.query.filter_by(trial_id=trial.id).first()
            self.question_id = question.id
            self.correct_index = question.correct_index
            db.session.commit()
            self.student_id = self.student.id
            self.student_token = create_access_token(identity=str(self.student_id))
            self.teacher_token = create_access_token(identity=str(teacher.id))

    def auth(self, token):
        return {'Authorization': f'Bearer {token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_mcq_wrong_creates_mistake(self):
        resp = self.client.post(
            f'/api/v1/student/assignments/{self.question_id}/answer',
            json={'selected_index': 0 if self.correct_index != 0 else 1},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(resp.status_code, 200)
        with self.app.app_context():
            row = StudentMistake.query.filter_by(
                user_id=self.student_id,
                source='mcq',
                question_ref=str(self.question_id),
            ).first()
            self.assertIsNotNone(row)
            self.assertGreaterEqual(row.fail_count, 1)

    def test_code_trial_run_and_list(self):
        run_resp = self.client.post(
            '/api/v1/student/code-trial/runs',
            json={
                'question_id': 'py-demo-01',
                'question_title': 'Hello World',
                'knowledge_key': 'lang',
                'topic': '输出',
                'tags': ['print'],
                'cases': [
                    {'label': '样例1', 'passed': False, 'error': 'wrong'},
                ],
            },
            headers=self.auth(self.student_token),
        )
        self.assertEqual(run_resp.status_code, 200)

        list_resp = self.client.get('/api/v1/student/mistakes', headers=self.auth(self.student_token))
        self.assertEqual(list_resp.status_code, 200)
        data = list_resp.get_json()['data']
        self.assertGreaterEqual(data['total'], 1)

    def test_teacher_can_view_student_mistakes(self):
        with self.app.app_context():
            from app.services.mistake import MistakeService

            MistakeService.record_code_trial_run(
                self.student_id,
                {
                    'question_id': 'py-teacher-view',
                    'cases': [{'label': 't', 'passed': False}],
                    'knowledge_key': 'algo',
                },
            )

        resp = self.client.get(
            f'/api/v1/teacher/students/{self.student_id}/mistakes',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()['data']['items']
        self.assertTrue(any(i['question_ref'] == 'py-teacher-view' for i in items))


if __name__ == '__main__':
    unittest.main()
