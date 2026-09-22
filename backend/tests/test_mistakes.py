"""错题本与 SM-2 复习闭环 API 测试"""
import unittest
from datetime import datetime

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, StudentMistake, Trial, TrialQuestion, User, db
from app.services.question_generator import QuestionGenerator
from app.services.mistake import MistakeService


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

    def test_code_trial_pass_creates_accepted_record(self):
        run_resp = self.client.post(
            '/api/v1/student/code-trial/runs',
            json={
                'question_id': 'gen-stage1-intro-s0',
                'question_title': 'Hello World',
                'knowledge_key': 'intro',
                'topic': '输出',
                'tags': ['intro'],
                'cases': [{'label': '样例1', 'passed': True}],
            },
            headers=self.auth(self.student_token),
        )
        self.assertEqual(run_resp.status_code, 200)

        path_resp = self.client.get('/api/v1/student/learning-path', headers=self.auth(self.student_token))
        self.assertEqual(path_resp.status_code, 200)
        ac_status = path_resp.get_json()['data'].get('question_ac_status', [])
        self.assertIn('gen-stage1-intro-s0', ac_status)

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

    def test_sm2_algorithm_uses_one_then_six_day_intervals(self):
        now = datetime(2026, 8, 28, 8, 0, 0)
        first = MistakeService.calculate_sm2(None, 5, now)
        self.assertEqual(first['repetitions'], 1)
        self.assertEqual(first['interval_days'], 1)
        second = MistakeService.calculate_sm2(first, 5, now)
        self.assertEqual(second['repetitions'], 2)
        self.assertEqual(second['interval_days'], 6)

    def test_wrong_answer_enters_due_queue_and_review_reschedules_it(self):
        run_resp = self.client.post(
            '/api/v1/student/code-trial/runs',
            json={
                'question_id': 'sm2-demo-01',
                'question_title': 'SM-2 闭环题',
                'knowledge_key': 'loop',
                'cases': [{'label': '样例1', 'passed': False}],
            },
            headers=self.auth(self.student_token),
        )
        self.assertEqual(run_resp.status_code, 200)
        mistake_id = run_resp.get_json()['data']['record']['id']

        due_resp = self.client.get(
            '/api/v1/student/mistakes/reviews/due',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(due_resp.status_code, 200)
        due_items = due_resp.get_json()['data']['items']
        self.assertTrue(any(item['id'] == mistake_id for item in due_items))

        review_resp = self.client.post(
            f'/api/v1/student/mistakes/{mistake_id}/review',
            json={'quality': 5},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(review_resp.status_code, 200)
        record = review_resp.get_json()['data']['record']
        self.assertEqual(record['review_schedule']['algorithm'], 'SM-2')
        self.assertEqual(record['review_schedule']['interval_days'], 1)
        self.assertEqual(record['review_schedule']['repetitions'], 1)
        self.assertEqual(
            review_resp.get_json()['data']['knowledge_graph_update']['status'],
            'learning',
        )

        due_again = self.client.get(
            '/api/v1/student/mistakes/reviews/due',
            headers=self.auth(self.student_token),
        )
        self.assertFalse(any(item['id'] == mistake_id for item in due_again.get_json()['data']['items']))

        second_review = self.client.post(
            f'/api/v1/student/mistakes/{mistake_id}/review',
            json={'quality': 5},
            headers=self.auth(self.student_token),
        )
        self.assertEqual(second_review.status_code, 200)
        update = second_review.get_json()['data']
        self.assertEqual(update['record']['review_schedule']['interval_days'], 6)
        self.assertEqual(update['knowledge_graph_update']['status'], 'mastered')
        self.assertEqual(update['knowledge_graph_update']['review_repetitions'], 2)
        self.assertGreaterEqual(update['student_profile_update']['version'], 2)
        self.assertEqual(update['student_profile_update']['reason'], 'sm2_review')
        self.assertIn(
            '两轮',
            update['student_profile_update']['dimensions']['knowledge_foundation']['value'],
        )
        self.assertTrue(update['learning_path_update']['replanned'])
        self.assertEqual(update['learning_path_update']['trigger'], 'sm2_review')
        self.assertNotEqual(update['learning_path_update']['active_node_id'], 'loop-for')
        path_diff = update['learning_path_update']['path_diff']
        self.assertIn('previous_active_node_id', path_diff)
        self.assertIn('current_active_node_id', path_diff)
        self.assertIsInstance(path_diff['changed'], bool)
        self.assertEqual(len(path_diff['previous_top_node_ids']), 5)
        self.assertEqual(len(path_diff['current_top_node_ids']), 5)

    def test_review_quality_validation(self):
        with self.app.app_context():
            with self.assertRaisesRegex(ValueError, '0 到 5'):
                MistakeService.calculate_sm2(None, 6)
            with self.assertRaisesRegex(ValueError, '0 到 5'):
                MistakeService.calculate_sm2(None, 4.5)


if __name__ == '__main__':
    unittest.main()
