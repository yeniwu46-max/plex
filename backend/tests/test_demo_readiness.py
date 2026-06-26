"""Regression coverage for the repeatable personalization demo flow."""
import unittest

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import Role, StudentProfileSuggestion, User, db
from app.services.mistake import MistakeService


class DemoReadinessTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student_a = User.query.filter_by(username='student001').first()
            student_b = User.query.filter_by(username='student002').first()
            if not student_b:
                student_role = Role.query.filter_by(name='student').first()
                student_b = User(
                    username='student002',
                    email='student002@example.com',
                    password_hash=generate_password_hash('student123'),
                    real_name='学生2',
                    role_id=student_role.id,
                )
                db.session.add(student_b)
                db.session.commit()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student_a_id = student_a.id
            self.student_tokens = {
                'a': create_access_token(identity=str(student_a.id)),
                'b': create_access_token(identity=str(student_b.id)),
            }
            self.teacher_token = create_access_token(identity=str(teacher.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def auth(token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def put_profile(self, key, changes):
        response = self.client.put(
            '/api/v1/student/profile',
            headers=self.auth(self.student_tokens[key]),
            json={'changes': changes},
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()['data']

    def generate(self, key, idempotency_key):
        response = self.client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=self.auth(self.student_tokens[key]),
            json={
                'knowledge_key': 'loop',
                'idempotency_key': idempotency_key,
                'force_regenerate': True,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()['data']

    def test_two_profiles_generate_explainably_different_resources(self):
        profiles = {
            'a': {
                'major_background': '非计算机专业大一',
                'knowledge_foundation': 'Python 零基础',
                'learning_goal': '掌握 Python 基础并完成校园小工具',
                'explanation_preference': '分步骤讲解和生活化案例',
                'mistake_pattern': '循环边界与缩进容易出错',
                'learning_pace': '每天 30 分钟',
                'interest_direction': '校园生活自动化',
            },
            'b': {
                'major_background': '软件工程专业',
                'knowledge_foundation': '具备 Python 基础',
                'learning_goal': '提升算法设计与复杂度分析能力',
                'explanation_preference': '先看代码，再做挑战题',
                'mistake_pattern': '复杂边界条件考虑不足',
                'learning_pace': '周末集中学习 3 小时',
                'interest_direction': '算法竞赛',
            },
        }
        profile_a = self.put_profile('a', profiles['a'])
        profile_b = self.put_profile('b', profiles['b'])
        self.assertEqual(profile_a['completion_rate'], 100)
        self.assertEqual(profile_b['completion_rate'], 100)
        self.assertTrue(all(
            item['source'] == 'confirmed'
            for item in profile_a['dimensions'].values()
        ))

        task_a = self.generate('a', 'demo-profile-a')
        task_b = self.generate('b', 'demo-profile-b')
        self.assertEqual(len(task_a['resources']), 5)
        self.assertEqual(len(task_b['resources']), 5)

        resources_a = {item['resource_type']: item for item in task_a['resources']}
        resources_b = {item['resource_type']: item for item in task_b['resources']}
        self.assertLess(
            resources_a['lesson_document']['difficulty'],
            resources_b['lesson_document']['difficulty'],
        )
        self.assertIn(
            profiles['a']['explanation_preference'],
            resources_a['lesson_document']['content']['markdown'],
        )
        self.assertIn(
            profiles['b']['explanation_preference'],
            resources_b['lesson_document']['content']['markdown'],
        )
        self.assertIn(
            profiles['a']['interest_direction'],
            resources_a['coding_lab']['content']['scenario'],
        )
        self.assertIn(
            profiles['b']['interest_direction'],
            resources_b['coding_lab']['content']['scenario'],
        )
        for task in (task_a, task_b):
            self.assertTrue(all(item['citations'] for item in task['resources']))
            self.assertTrue(all(item['backend'] == 'local_rules' for item in task['resources']))
            pending = [
                item for item in task['resources']
                if item['review_status'] == 'pending_review'
            ]
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]['resource_type'], 'extended_reading')
            self.assertIn('low_confidence', pending[0]['risk_reasons'])

    def test_feedback_accept_reject_and_teacher_review_flow(self):
        profile = self.put_profile('a', {
            'major_background': '计算机专业大一',
            'knowledge_foundation': 'Python 零基础',
            'learning_goal': '掌握 Python 基础',
            'explanation_preference': '代码案例优先、分步骤讲解',
            'mistake_pattern': '尚未形成稳定模式',
            'learning_pace': '每天 30 分钟',
            'interest_direction': '数据处理',
        })
        initial_version = profile['version']
        task_before_feedback = self.generate('a', 'demo-feedback-order')

        with self.app.app_context():
            MistakeService._upsert(
                self.student_a_id,
                source='code_trial',
                knowledge_key='loop',
                question_ref='demo-accept',
                question_title='循环边界',
                error_type='wrong_output',
            )

        before = self.client.get(
            '/api/v1/student/recommendations',
            headers=self.auth(self.student_tokens['a']),
        ).get_json()['data']
        suggestion = before['profile_update_suggestion']
        self.assertIsNotNone(suggestion)
        path_before = self.client.get(
            '/api/v1/student/learning-path',
            headers=self.auth(self.student_tokens['a']),
        ).get_json()['data']
        before_resource_ids = [
            item['id'] for item in before['personalized_resources']
        ]
        self.assertTrue(before_resource_ids)
        self.assertEqual(
            before['personalized_resources'][0]['resource_type'],
            'coding_lab',
        )
        denied_teacher = self.client.put(
            f"/api/v1/student/profile/suggestions/{suggestion['id']}",
            headers=self.auth(self.teacher_token),
            json={'action': 'accepted'},
        )
        self.assertEqual(denied_teacher.status_code, 403)
        denied_other_student = self.client.put(
            f"/api/v1/student/profile/suggestions/{suggestion['id']}",
            headers=self.auth(self.student_tokens['b']),
            json={'action': 'accepted'},
        )
        self.assertEqual(denied_other_student.status_code, 404)
        accepted = self.client.put(
            f"/api/v1/student/profile/suggestions/{suggestion['id']}",
            headers=self.auth(self.student_tokens['a']),
            json={'action': 'accepted'},
        )
        self.assertEqual(accepted.status_code, 200)
        accepted_data = accepted.get_json()['data']
        self.assertGreater(accepted_data['profile']['version'], initial_version)
        after_accept = self.client.get(
            '/api/v1/student/recommendations',
            headers=self.auth(self.student_tokens['a']),
        ).get_json()['data']
        self.assertEqual(after_accept['profile_version'], accepted_data['profile']['version'])
        self.assertIn('loop', after_accept['recommendation_context']['weak_knowledge'])
        self.assertEqual(
            after_accept['recommendation_context']['preferred_resource_types'][:2],
            ['exercise_set', 'coding_lab'],
        )
        self.assertEqual(
            after_accept['personalized_resources'][0]['resource_type'],
            'exercise_set',
        )
        self.assertNotEqual(
            before_resource_ids,
            [item['id'] for item in after_accept['personalized_resources']],
        )
        path_after = self.client.get(
            '/api/v1/student/learning-path',
            headers=self.auth(self.student_tokens['a']),
        ).get_json()['data']
        stage2_before = next(
            item for item in path_before['domains'] if item['key'] == 'stage2'
        )
        stage2_after = next(
            item for item in path_after['domains'] if item['key'] == 'stage2'
        )
        self.assertNotEqual(
            stage2_before['recommended_resource_ids'],
            stage2_after['recommended_resource_ids'],
        )
        self.assertIn('近期薄弱点', stage2_after['recommendation_reason'])
        self.assertEqual(task_before_feedback['profile_version'], initial_version)

        with self.app.app_context():
            MistakeService._upsert(
                self.student_a_id,
                source='code_trial',
                knowledge_key='range',
                question_ref='demo-reject',
                question_title='range 边界',
                error_type='wrong_output',
            )
            pending = StudentProfileSuggestion.query.filter_by(
                user_id=self.student_a_id,
                status='pending',
            ).first()
            self.assertIsNotNone(pending)
            pending_id = pending.id

        version_before_reject = after_accept['profile_version']
        rejected = self.client.put(
            f'/api/v1/student/profile/suggestions/{pending_id}',
            headers=self.auth(self.student_tokens['a']),
            json={'action': 'rejected'},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertIsNone(rejected.get_json()['data']['profile'])
        after_reject = self.client.get(
            '/api/v1/student/recommendations',
            headers=self.auth(self.student_tokens['a']),
        ).get_json()['data']
        self.assertEqual(after_reject['profile_version'], version_before_reject)

        task = self.generate('a', 'demo-review')
        pending_resource = next(
            item for item in task['resources']
            if item['review_status'] == 'pending_review'
        )
        student_listing = self.client.get(
            '/api/v1/student/personalized-resources',
            headers=self.auth(self.student_tokens['a']),
        ).get_json()['data']
        self.assertNotIn(
            pending_resource['id'],
            {item['id'] for item in student_listing['items']},
        )
        review_listing = self.client.get(
            '/api/v1/teacher/personalized-resources/review',
            headers=self.auth(self.teacher_token),
        ).get_json()['data']
        self.assertIn(
            pending_resource['id'],
            {item['id'] for item in review_listing['items']},
        )
        approved = self.client.put(
            f"/api/v1/teacher/personalized-resources/{pending_resource['id']}/review",
            headers=self.auth(self.teacher_token),
            json={'review_status': 'approved', 'reason': '演示彩排核验通过'},
        )
        self.assertEqual(approved.status_code, 200)
        refreshed = self.client.get(
            '/api/v1/student/personalized-resources',
            headers=self.auth(self.student_tokens['a']),
        ).get_json()['data']
        self.assertIn(
            pending_resource['id'],
            {item['id'] for item in refreshed['items']},
        )


if __name__ == '__main__':
    unittest.main()
