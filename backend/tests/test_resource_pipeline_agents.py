# -*- coding: utf-8 -*-
import unittest

from app import create_app


class ResourcePipelineAgentsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')

    def test_knowledge_retriever_references_course_section(self):
        with self.app.app_context():
            from app.services.personalized_resource import PersonalizedResourceService

            profile = {'knowledge_foundation': '零基础', 'interest_direction': '游戏'}
            strategy, backend, model = PersonalizedResourceService._run_profile_interpreter(
                profile, 'loop'
            )
            self.assertEqual(backend, 'local_rules')
            self.assertIn('profile_rationale', strategy)

            knowledge, kb_backend, _ = PersonalizedResourceService._run_knowledge_retriever(
                'loop', strategy
            )
            self.assertEqual(kb_backend, 'local_rules')
            self.assertTrue(knowledge.get('course_section'))
            self.assertTrue(knowledge.get('retrieved_passages') or knowledge.get('retrieved_snippet'))
            self.assertIn('retrieval_rationale', knowledge)

            design, design_backend, _ = PersonalizedResourceService._run_instructional_designer(
                ['learning_bundle', 'lesson_document'],
                strategy,
                knowledge,
                {'target': '大学', 'learning_stage': '学习', 'learning_style': ['案例']},
                profile,
            )
            self.assertEqual(design_backend, 'local_rules')
            self.assertIn('design_rationale', design)
            self.assertTrue(design.get('sequence'))


if __name__ == '__main__':
    unittest.main()
