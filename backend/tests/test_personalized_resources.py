import unittest

from flask_jwt_extended import create_access_token

from app import create_app
from app.models import PersonalizedLearningResource, ResourceGenerationTask, User, db


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

    def test_generate_five_resources_and_list(self):
        response = self.client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=self.auth(self.student_token),
            json={'knowledge_key': 'loop'},
        )
        self.assertEqual(response.status_code, 201)
        task = response.get_json()['data']
        self.assertEqual(task['status'], 'completed')
        self.assertEqual(task['progress'], 100)
        self.assertEqual(len(task['resources']), 5)
        self.assertEqual({item['resource_type'] for item in task['resources']}, {
            'lesson_document', 'mind_map', 'exercise_set', 'extended_reading', 'coding_lab'
        })
        self.assertTrue(all(item['citations'] for item in task['resources']))
        self.assertTrue(all(
            item['citations'][0]['document_id'] == 'python-stage2-loop'
            for item in task['resources']
        ))
        self.assertTrue(all(item['review_status'] == 'approved' for item in task['resources']))
        self.assertTrue(all(item['backend'] == 'local_rules' for item in task['resources']))

        listing = self.client.get(
            '/api/v1/student/personalized-resources',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.get_json()['data']['total'], 5)

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


if __name__ == '__main__':
    unittest.main()
