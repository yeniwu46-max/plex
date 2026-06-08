import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from flask_jwt_extended import create_access_token
import requests

from app import create_app
from app.models import ResourceGenerationTask, StudentProfileSuggestion, User, db
from app.services.iflytek_spark import IflytekSparkService, SparkServiceError
from app.services.mistake import MistakeService
from app.services.personalized_resource import PersonalizedResourceService


class StabilityTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            student = User.query.filter_by(username='student001').first()
            teacher = User.query.filter_by(username='teacher001').first()
            self.student_id = student.id
            self.student_token = create_access_token(identity=str(student.id))
            self.teacher_token = create_access_token(identity=str(teacher.id))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @staticmethod
    def auth(token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    def test_health_endpoints_are_secret_free(self):
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()['data']
        self.assertEqual(body['database'], 'healthy')
        self.assertNotIn('password', json.dumps(body).lower())

        ai = self.client.get('/api/v1/system/ai-health').get_json()['data']
        self.assertTrue(ai['fallback']['available'])
        self.assertNotIn('api_password', json.dumps(ai).lower())

    def test_spark_success_and_error_classification(self):
        response = Mock()
        response.status_code = 200
        response.headers = {'x-request-id': 'req-test'}
        response.json.return_value = {
            'choices': [{'message': {'content': '{"ok": true}'}}],
        }
        with patch.dict(os.environ, {'IFLYTEK_SPARK_API_PASSWORD': 'test-only'}):
            with patch('app.services.iflytek_spark.requests.post', return_value=response):
                result = IflytekSparkService.chat_json('system', 'user')
        self.assertTrue(result['ok'])
        self.assertEqual(IflytekSparkService.status()['request_id'], 'req-test')

        response.status_code = 429
        with patch.dict(os.environ, {'IFLYTEK_SPARK_API_PASSWORD': 'test-only'}):
            with patch('app.services.iflytek_spark.requests.post', return_value=response):
                with self.assertRaises(SparkServiceError) as context:
                    IflytekSparkService.chat_json('system', 'user')
        self.assertEqual(context.exception.code, 'rate_limited')

        cases = [
            (401, {'choices': []}, 'authentication_failed'),
            (200, {'choices': []}, 'invalid_response'),
            (200, {'choices': [{'message': {'content': ''}}]}, 'empty_response'),
            (200, {'choices': [{'message': {'content': 'not-json'}}]}, 'invalid_json'),
        ]
        for status, payload, expected in cases:
            response.status_code = status
            response.json.return_value = payload
            with patch.dict(os.environ, {'IFLYTEK_SPARK_API_PASSWORD': 'test-only'}):
                with patch('app.services.iflytek_spark.requests.post', return_value=response):
                    with self.assertRaises(SparkServiceError) as context:
                        IflytekSparkService.chat_json('system', 'user')
            self.assertEqual(context.exception.code, expected)

        with patch.dict(os.environ, {'IFLYTEK_SPARK_API_PASSWORD': 'test-only'}):
            with patch('app.services.iflytek_spark.requests.post', side_effect=requests.Timeout()):
                with self.assertRaises(SparkServiceError) as context:
                    IflytekSparkService.chat_json('system', 'user')
        self.assertEqual(context.exception.code, 'timeout')

    def test_task_idempotency_history_and_atomic_claim(self):
        first = self.client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=self.auth(self.student_token),
            json={'knowledge_key': 'loop', 'idempotency_key': 'same-request'},
        ).get_json()['data']
        second = self.client.post(
            '/api/v1/student/resource-generation/tasks',
            headers=self.auth(self.student_token),
            json={'knowledge_key': 'loop', 'idempotency_key': 'same-request'},
        ).get_json()['data']
        self.assertEqual(first['task_id'], second['task_id'])
        self.assertEqual(first['profile_version'], second['profile_version'])
        with self.app.app_context():
            PersonalizedResourceService.run_task(self.app, first['task_id'])
            self.assertEqual(ResourceGenerationTask.query.count(), 1)

        history = self.client.get(
            '/api/v1/student/resource-generation/tasks',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.get_json()['data']['total'], 1)

    def test_stale_task_becomes_recoverable_failure_and_retry(self):
        with self.app.app_context():
            row = ResourceGenerationTask(
                task_id='rg_stale',
                user_id=self.student_id,
                knowledge_key='loop',
                requested_types=['lesson_document'],
                status='running',
                progress=40,
                updated_at=datetime.utcnow() - timedelta(minutes=20),
            )
            db.session.add(row)
            db.session.commit()
            PersonalizedResourceService.recover_stale_tasks()
            db.session.refresh(row)
            self.assertEqual(row.status, 'failed')
            self.assertTrue(row.recoverable)

        response = self.client.post(
            '/api/v1/student/resource-generation/tasks/rg_stale/retry',
            headers=self.auth(self.student_token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['data']['retry_of'], 'rg_stale')

    def test_invalid_resource_risks(self):
        risks = PersonalizedResourceService._risk_reasons({
            'resource_type': 'coding_lab',
            'content': {
                'format': 'coding_lab',
                'scenario': '一个足够长的课程范围练习场景',
                'starter_code': 'if True print("x")',
                'checks': ['可运行'],
            },
            'confidence': 0.5,
            'citations': [{'document_id': 'fake', 'section': 'loop'}],
        }, 'loop')
        self.assertIn('low_confidence', risks)
        self.assertIn('invalid_citation', risks)
        self.assertIn('schema_invalid', risks)

    def test_mistake_suggestion_acceptance_and_permissions(self):
        with self.app.app_context():
            MistakeService._upsert(
                self.student_id,
                source='code_trial',
                knowledge_key='loop',
                question_ref='stability-loop',
                question_title='循环边界',
                error_type='wrong_output',
            )
            self.assertEqual(StudentProfileSuggestion.query.count(), 1)

        suggestions = self.client.get(
            '/api/v1/student/profile/suggestions',
            headers=self.auth(self.student_token),
        ).get_json()['data']
        suggestion = suggestions['items'][0]
        accepted = self.client.put(
            f"/api/v1/student/profile/suggestions/{suggestion['id']}",
            headers=self.auth(self.student_token),
            json={'action': 'accepted'},
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.get_json()['data']['suggestion']['status'], 'accepted')
        self.assertGreaterEqual(accepted.get_json()['data']['profile']['version'], 2)

        forbidden = self.client.get(
            '/api/v1/student/profile/suggestions',
            headers=self.auth(self.teacher_token),
        )
        self.assertEqual(forbidden.status_code, 403)


if __name__ == '__main__':
    unittest.main()
