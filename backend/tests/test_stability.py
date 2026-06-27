import json
import os
import unittest
from datetime import timedelta
from unittest.mock import Mock, patch

from flask_jwt_extended import create_access_token
import requests

from app import create_app
from app.models import ResourceGenerationTask, StudentProfileSuggestion, User, db
from app.services.iflytek_spark import IflytekSparkService, SparkServiceError
from app.services.mistake import MistakeService
from app.services.personalized_resource import PersonalizedResourceService
from app.services.xfyun_agent import XfyunAgentService
from app.utils.time import utc_now


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

        response.json.return_value = {
            'choices': [{'message': {'content': '结果如下：\n```json\n{"ok": true}\n```'}}],
        }
        with patch.dict(os.environ, {'IFLYTEK_SPARK_API_PASSWORD': 'test-only'}):
            with patch('app.services.iflytek_spark.requests.post', return_value=response):
                self.assertTrue(IflytekSparkService.chat_json('system', 'user')['ok'])

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

    def test_xfyun_agent_api_request_and_response_parsing(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            'choices': [{'message': {'content': '可以先用 print 输出变量，再检查循环边界。'}}],
        }
        self.app.config['XFYUN_AGENT_ALLOW_IN_TESTS'] = True
        with patch.dict(os.environ, {
            'XFYUN_AGENT_FLOW_ID': 'flow-test',
            'XFYUN_AGENT_API_KEY': 'key-test',
            'XFYUN_AGENT_API_SECRET': 'secret-test',
            'XFYUN_AGENT_BOT_ID': '2208791',
        }):
            with patch('app.services.xfyun_agent.requests.post', return_value=response) as post:
                result = XfyunAgentService.chat_text(user_id=self.student_id, message='Python print 怎么用？', context='课程：Python 入门')

        self.assertIn('print', result)
        request_kwargs = post.call_args.kwargs
        self.assertEqual(request_kwargs['headers']['Authorization'], 'Bearer key-test:secret-test')
        self.assertEqual(request_kwargs['json']['flow_id'], 'flow-test')
        self.assertEqual(request_kwargs['json']['ext']['bot_id'], '2208791')
        self.assertEqual(request_kwargs['proxies'], {'http': '', 'https': ''})
        self.assertIn('Python print 怎么用？', request_kwargs['json']['parameters']['AGENT_USER_INPUT'])

        response.json.return_value = {
            'code': 0,
            'message': 'Success',
            'choices': [{'delta': {'content': '这是工作流非流式返回。'}}],
        }
        with patch.dict(os.environ, {
            'XFYUN_AGENT_FLOW_ID': 'flow-test',
            'XFYUN_AGENT_API_KEY': 'key-test',
            'XFYUN_AGENT_API_SECRET': 'secret-test',
        }):
            with patch('app.services.xfyun_agent.requests.post', return_value=response):
                self.assertIn('工作流', XfyunAgentService.chat_text(user_id=self.student_id, message='测试', context=''))

        response.json.return_value = {
            'code': 20207,
            'message': 'flow id 状态为草稿，请发布',
            'choices': [{'delta': {'content': ''}}],
        }
        with patch.dict(os.environ, {
            'XFYUN_AGENT_FLOW_ID': 'flow-test',
            'XFYUN_AGENT_API_KEY': 'key-test',
            'XFYUN_AGENT_API_SECRET': 'secret-test',
        }):
            with patch('app.services.xfyun_agent.requests.post', return_value=response):
                with self.assertRaises(Exception) as context:
                    XfyunAgentService.chat_text(user_id=self.student_id, message='测试', context='')
        self.assertIn('草稿', str(context.exception))

    def test_xfyun_agent_rejects_placeholder_response(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            'code': 0,
            'choices': [{'message': {'content': '{{str_output}}\n'}}],
        }
        self.app.config['XFYUN_AGENT_ALLOW_IN_TESTS'] = True
        with patch.dict(os.environ, {
            'XFYUN_AGENT_FLOW_ID': 'flow-test',
            'XFYUN_AGENT_API_KEY': 'key-test',
            'XFYUN_AGENT_API_SECRET': 'secret-test',
        }):
            with patch('app.services.xfyun_agent.requests.post', return_value=response):
                with self.assertRaises(Exception) as context:
                    XfyunAgentService.chat_text(user_id=self.student_id, message='test', context='')
        self.assertEqual(context.exception.code, 'placeholder_response')

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
                updated_at=utc_now() - timedelta(minutes=20),
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
