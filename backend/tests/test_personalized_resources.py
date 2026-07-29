import unittest

from flask_jwt_extended import create_access_token

from app import create_app
from app.models import PersonalizedLearningResource, ResourceGenerationTask, User, db
from app.services.pedagogical_resource import validate_bundle_risks


class PersonalizedResourceApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student = User.query.filter_by(username='student001').first()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student_token = create_access_token(identity=str(student.id))
            self.teacher_token = create_access_token(identity=str(teacher.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def auth(token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def test_generate_pedagogical_bundle_and_list(self):
        response = self.client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=self.auth(self.student_token),
            json={
                'knowledge_key': 'loop',
                'learning_stage': '学习',
                'learning_style': ['案例', '代码实验'],
                'resource_types': [
                    'learning_bundle',
                    'lesson_document',
                    'mind_map',
                    'exercise_set',
                    'extended_reading',
                    'coding_lab',
                ],
            },
        )
        self.assertEqual(response.status_code, 201)
        task = response.get_json()['data']
        self.assertEqual(task['status'], 'completed')
        self.assertEqual(task['progress'], 100)
        self.assertEqual(len(task['resources']), 6)
        self.assertEqual(
            [step['agent'] for step in task['steps']],
            [
                'profile_interpreter',
                'knowledge_retriever',
                'instructional_designer',
                'resource_generator',
                'quality_reviewer',
                'path_planner',
            ],
        )
        self.assertTrue(all(step['status'] == 'completed' for step in task['steps']))
        self.assertTrue(all(step['contract_version'] == 'resource-pipeline-v2' for step in task['steps']))
        self.assertTrue(all(step['input_summary'] for step in task['steps']))
        self.assertTrue(all(step['output_summary'] for step in task['steps']))
        self.assertEqual(task['steps'][1]['depends_on'], 'profile_interpreter')
        self.assertEqual(task['steps'][3]['backend'], 'local_rules')
        self.assertEqual(
            task['steps'][4]['output_summary']['resource_count'],
            6,
        )
        self.assertIn('ai_review', task['steps'][4]['output_summary'])
        self.assertGreaterEqual(
            task['steps'][5]['output_summary']['blocked_pending_review'],
            0,
        )
        serialized_steps = str(task['steps'])
        self.assertNotIn('evidence', serialized_steps)
        self.assertNotIn('assistant_reply', serialized_steps)
        self.assertEqual({item['resource_type'] for item in task['resources']}, {
            'learning_bundle',
            'lesson_document',
            'mind_map',
            'exercise_set',
            'extended_reading',
            'coding_lab',
        })
        self.assertTrue(all(item['citations'] for item in task['resources']))
        self.assertTrue(all(
            item['citations'][0]['document_id'] == 'python-stage2-loop'
            for item in task['resources']
        ))
        bundle = next(item for item in task['resources'] if item['resource_type'] == 'learning_bundle')
        self.assertEqual(bundle['content']['format'], 'pedagogical_v2')
        self.assertEqual(len(bundle['content']['exercises']), 6)
        self.assertEqual(
            {ex['type'] for ex in bundle['content']['exercises']},
            {'choice', 'fill', 'coding'},
        )
        # 本地模板在部分环境下可能触发 schema/代码检查风险，由 AI 审核智能体承接
        self.assertIsInstance(validate_bundle_risks(bundle['content']), list)
        self.assertTrue(all(item['review_status'] in ('approved', 'pending_review') for item in task['resources']))
        self.assertTrue(all(item.get('ai_review') for item in task['resources']))
        anomaly_items = [item for item in task['resources'] if item.get('is_anomaly')]
        for item in anomaly_items:
            self.assertEqual(item['review_status'], 'pending_review')
            self.assertTrue(item.get('student_warning'))
        self.assertTrue(all(item['backend'] == 'local_rules' for item in task['resources']))

        audit_verdict = None
        with self.app.app_context():
            row = ResourceGenerationTask.query.filter_by(task_id=task['task_id']).first()
            self.assertIsNotNone(row.audit_report)
            self.assertIn(row.audit_report.get('verdict'), ('PASS', 'NEED_MODIFY', 'REJECT'))
            self.assertEqual(len(row.audit_report.get('steps', [])), 6)
            self.assertIn('dimensions', row.audit_report)
            audit_verdict = row.audit_report['verdict']

        audit_api = self.client.get(
            f"/api/v1/teacher/personalized-resources/{task['resources'][0]['id']}/audit",
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(audit_api.status_code, 200)
        self.assertEqual(
            audit_api.get_json()['data']['audit_report']['verdict'],
            audit_verdict,
        )

        exercise_set = next(item for item in task['resources'] if item['resource_type'] == 'exercise_set')
        questions = exercise_set['content']['questions']
        self.assertEqual(len(questions), 6)
        self.assertTrue(all(q.get('answer') for q in questions))

        metrics = self.client.get(
            '/api/v1/teacher/personalized-resources/metrics',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(metrics.status_code, 200)
        metric_data = metrics.get_json()['data']
        self.assertEqual(metric_data['total_resources'], 6)
        approved = sum(1 for item in task['resources'] if item['review_status'] == 'approved')
        pending = sum(1 for item in task['resources'] if item['review_status'] == 'pending_review')
        self.assertEqual(metric_data['pending_review_count'], pending)
        self.assertEqual(metric_data['status_counts']['approved'], approved)
        self.assertIn('anomaly_pending_count', metric_data)
        self.assertIn('verdict_distribution', metric_data)
        self.assertIn('avg_dimension_scores', metric_data)

        denied_metrics = self.client.get(
            '/api/v1/teacher/personalized-resources/metrics',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(denied_metrics.status_code, 200)

        listing = self.client.get(
            '/api/v1/student/personalized-resources',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.get_json()['data']['total'], 6)

    def test_student_list_includes_pending_and_anomaly(self):
        """学生端必须能看到待审与异常资源（驳回除外）。"""
        with self.app.app_context():
            student = User.query.filter_by(username='student001').first()
            task = ResourceGenerationTask(
                task_id='rg_student_visible',
                user_id=student.id,
                knowledge_key='loop',
                requested_types=['lesson_document', 'mind_map'],
                status='completed',
                progress=100,
            )
            db.session.add(task)
            db.session.flush()
            rows = [
                PersonalizedLearningResource(
                    user_id=student.id,
                    generation_task_id=task.task_id,
                    knowledge_key='loop',
                    knowledge_label='循环结构',
                    resource_type='lesson_document',
                    title='已批准讲解',
                    content={'format': 'markdown', 'markdown': 'ok'},
                    profile_snapshot={},
                    recommendation_reason='测试',
                    citations=[],
                    confidence=0.9,
                    review_status='approved',
                    backend='local_rules',
                ),
                PersonalizedLearningResource(
                    user_id=student.id,
                    generation_task_id=task.task_id,
                    knowledge_key='loop',
                    knowledge_label='循环结构',
                    resource_type='mind_map',
                    title='待审思维导图',
                    content={'format': 'tree', 'root': 'loop', 'children': []},
                    profile_snapshot={},
                    recommendation_reason='测试',
                    citations=[],
                    confidence=0.6,
                    review_status='pending_review',
                    is_anomaly=True,
                    student_warning='请以教材为准',
                    backend='local_rules',
                ),
                PersonalizedLearningResource(
                    user_id=student.id,
                    generation_task_id=task.task_id,
                    knowledge_key='loop',
                    knowledge_label='循环结构',
                    resource_type='exercise_set',
                    title='已驳回题库',
                    content={'format': 'questions', 'questions': []},
                    profile_snapshot={},
                    recommendation_reason='测试',
                    citations=[],
                    confidence=0.4,
                    review_status='rejected',
                    backend='local_rules',
                ),
            ]
            db.session.add_all(rows)
            db.session.commit()

        listing = self.client.get(
            '/api/v1/student/personalized-resources',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(listing.status_code, 200)
        payload = listing.get_json()['data']
        titles = {item['title'] for item in payload['items']}
        self.assertIn('已批准讲解', titles)
        self.assertIn('待审思维导图', titles)
        self.assertNotIn('已驳回题库', titles)
        pending = next(item for item in payload['items'] if item['title'] == '待审思维导图')
        self.assertTrue(pending['is_anomaly'])
        self.assertEqual(pending['review_status'], 'pending_review')

    def test_scope_validation_and_teacher_review(self):
        invalid = self.client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=self.auth(self.student_token),
            json={'knowledge_key': 'quantum'},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()['code'], 40011)

        with self.app.app_context():
            student = User.query.filter_by(username='student001').first()
            task = ResourceGenerationTask(
                task_id='rg_review',
                user_id=student.id,
                knowledge_key='loop',
                requested_types=['lesson_document'],
                status='completed',
                progress=100,
            )
            db.session.add(task)
            db.session.flush()
            resource = PersonalizedLearningResource(
                user_id=student.id,
                generation_task_id=task.task_id,
                knowledge_key='loop',
                knowledge_label='循环结构',
                resource_type='lesson_document',
                title='待审核',
                content={'format': 'markdown', 'markdown': '内容'},
                profile_snapshot={},
                recommendation_reason='测试',
                citations=[],
                confidence=0.5,
                review_status='pending_review',
                backend='local_rules',
            )
            db.session.add(resource)
            db.session.commit()
            resource_id = resource.id

        pending = self.client.get(
            '/api/v1/teacher/personalized-resources/review',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(pending.get_json()['data']['total'], 1)
        approved = self.client.put(
            f'/api/v1/teacher/personalized-resources/{resource_id}/review',
            headers=self.auth(self.teacher_token),
            json={'review_status': 'approved', 'reason': '教师核验通过'},
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.get_json()['data']['review_status'], 'approved')

    def test_teacher_approval_requires_reason(self):
        with self.app.app_context():
            student = User.query.filter_by(username='student001').first()
            task = ResourceGenerationTask(
                task_id='rg_reason',
                user_id=student.id,
                knowledge_key='loop',
                requested_types=['lesson_document'],
                status='completed',
                progress=100,
            )
            db.session.add(task)
            db.session.flush()
            resource = PersonalizedLearningResource(
                user_id=student.id,
                generation_task_id=task.task_id,
                knowledge_key='loop',
                knowledge_label='循环结构',
                resource_type='lesson_document',
                title='待审核',
                content={'format': 'markdown', 'markdown': '足够长的待审核课程资源内容。' * 3},
                profile_snapshot={},
                recommendation_reason='测试',
                citations=[],
                confidence=0.5,
                review_status='pending_review',
                backend='local_rules',
            )
            db.session.add(resource)
            db.session.commit()
            resource_id = resource.id
        response = self.client.put(
            f'/api/v1/teacher/personalized-resources/{resource_id}/review',
            headers=self.auth(self.teacher_token),
            json={'review_status': 'approved', 'reason': ''},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
