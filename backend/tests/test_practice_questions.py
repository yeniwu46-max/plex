"""学生端编程练习题库 API。"""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Class, Role, Trial, TrialQuestion, User, db
from app.services.practice_question import PracticeQuestionService


class PracticeQuestionsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            teacher_role = Role.query.filter_by(name='teacher').first()
            student_role = Role.query.filter_by(name='student').first()
            teacher = User(
                username='practice-teacher',
                email='practice-teacher@example.com',
                password_hash=generate_password_hash('teacher123'),
                real_name='练习导师',
                role_id=teacher_role.id,
            )
            student = User(
                username='practice-student',
                email='practice-student@example.com',
                password_hash=generate_password_hash('student123'),
                real_name='练习同学',
                role_id=student_role.id,
            )
            db.session.add_all([teacher, student])
            db.session.flush()
            class_obj = Class(name='练习班', teacher_id=teacher.id, join_code='PRAC01')
            db.session.add(class_obj)
            db.session.flush()
            trial = Trial(
                class_id=class_obj.id,
                teacher_id=teacher.id,
                title='导入题库',
                trial_type='imported_coding',
                status='ended',
            )
            trial.set_knowledge_keys(['loop'])
            db.session.add(trial)
            db.session.flush()
            question = TrialQuestion(
                trial_id=trial.id,
                sort_order=1,
                question_type='coding',
                stem='输出 1 到 n 的累加和',
                options=[],
                correct_index=0,
                knowledge_key='loop',
            )
            question.set_coding_meta({
                'starter_code': '# n 已给定\n',
                'run_mode': 'stdout',
                'hint': '循环累加',
                'test_cases': [{'id': 't1', 'label': 'n=3', 'setup': 'n = 3', 'expected': '6'}],
                'source_problem_id': 9001,
            })
            db.session.add(question)
            db.session.commit()
            self.student_token = create_access_token(identity=str(student.id))
            self.imported_id = f'lc-{question.id}'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_list_practice_questions_includes_imported(self):
        resp = self.client.get(
            '/api/v1/student/practice-questions?knowledge_key=loop',
            headers={'Authorization': f'Bearer {self.student_token}'},
        )
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()['data']['items']
        ids = {item['id'] for item in items}
        self.assertIn(self.imported_id, ids)
        imported = next(item for item in items if item['id'] == self.imported_id)
        self.assertTrue(imported.get('code', '').startswith('L'))
        self.assertIn(' · ', imported['title'])

    def test_search_and_get_practice_question(self):
        search_resp = self.client.get(
            '/api/v1/student/practice-questions?q=累加',
            headers={'Authorization': f'Bearer {self.student_token}'},
        )
        self.assertEqual(search_resp.status_code, 200)
        search_items = search_resp.get_json()['data']['items']
        self.assertTrue(any(item['id'] == self.imported_id for item in search_items))

        detail_resp = self.client.get(
            f'/api/v1/student/practice-questions/{self.imported_id}',
            headers={'Authorization': f'Bearer {self.student_token}'},
        )
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.get_json()['data']['id'], self.imported_id)

    def test_extract_embedded_tests_from_stem(self):
        stem = '编写程序输出三科总分\n### 测试样例\n输入数据 70 80 90\n输出结果 240'
        clean, examples, tests = PracticeQuestionService._normalize_question_payload(stem, [], [])
        self.assertNotIn('###', clean)
        self.assertNotIn('输入数据', clean)
        self.assertTrue(examples)
        self.assertTrue(tests)
        self.assertEqual(examples[0]['output'], '240')
