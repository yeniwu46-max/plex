# -*- coding: utf-8 -*-
import unittest

from app import create_app


class ResourceReviewAgentTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')

    def test_rules_fallback_auto_approve_when_clean(self):
        with self.app.app_context():
            from agents.resource_review_agent import review_generated_resource

            result = review_generated_resource(
                bundle={'node': 'loop', 'cases': [{}], 'exercises': [{}, {}]},
                knowledge_key='loop',
                audit_report={
                    'verdict': 'PASS',
                    'suggested_publish': True,
                    'dimensions': {
                        'knowledge_accuracy': 90,
                        'teaching_quality': 88,
                        'case_quality': 85,
                        'exercise_quality': 86,
                        'code_quality': 90,
                        'ai_trustworthiness': 92,
                    },
                },
                risk_reasons=[],
            )
            self.assertEqual(result['decision'], 'auto_approve')
            self.assertFalse(result['is_anomaly'])
            self.assertEqual(result['student_warning'], '')

    def test_rules_fallback_flags_anomaly(self):
        with self.app.app_context():
            from agents.resource_review_agent import review_generated_resource

            result = review_generated_resource(
                bundle={'node': 'loop'},
                knowledge_key='loop',
                audit_report={
                    'verdict': 'NEED_MODIFY',
                    'suggested_publish': False,
                    'dimensions': {'knowledge_accuracy': 30},
                },
                risk_reasons=['low_confidence'],
            )
            self.assertEqual(result['decision'], 'needs_review')
            self.assertTrue(result['is_anomaly'])
            self.assertTrue(result['student_warning'])


if __name__ == '__main__':
    unittest.main()
