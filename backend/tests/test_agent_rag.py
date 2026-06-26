# -*- coding: utf-8 -*-
import unittest

from app import create_app
from app.services.agent_orchestrator import AgentOrchestrator
from agents.crew import run_learning_path_plan, run_student_diagnose, run_teacher_suggestion


class AgentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_student_diagnose_mock_pipeline(self):
        payload = {
            'code': 'for i in range(1, n):\n    s += i',
            'stderr': 'wrong answer',
            'knowledgePoints': ['for 循环', 'range'],
            'attemptCount': 2,
        }
        result = run_student_diagnose(payload)
        self.assertIn('diagnosis', result)
        self.assertIn('codeAnalysis', result)
        self.assertIn('graphInsight', result)
        self.assertIn('recommendation', result)
        self.assertIn('feedback', result)
        self.assertTrue(result['feedback']['stepHints'])
        self.assertLessEqual(len(result['feedback']['stepHints']), 3)

        # 四层错因模型新字段
        diagnosis = result['diagnosis']
        self.assertIn(diagnosis['errorLayer'], ('syntax', 'rule', 'logic', 'transfer', 'none'))
        self.assertIn('proficiency', diagnosis)
        self.assertIn('remediationStrategy', diagnosis)
        self.assertIn('relatedKnowledgePoints', diagnosis)
        # 向后兼容字段仍在
        self.assertIn('errorType', diagnosis)
        self.assertIn('weakPoints', diagnosis)

        # 显性化流水线轨迹
        self.assertIn('pipelineTrace', result)
        self.assertEqual(len(result['pipelineTrace']), 5)
        self.assertEqual(result['pipelineTrace'][0]['agentId'], 'learning_diagnosis')
        self.assertTrue(result['pipelineTrace'][0]['summary'])
        self.assertEqual(result['pipelineTrace'][3]['agentId'], 'learning_path')

    def test_learning_path_plan(self):
        result = run_learning_path_plan({'user_id': 1, 'focus_node_id': 'loop'})
        self.assertIn('ordered_nodes', result)
        self.assertIn('next_best_action', result)
        self.assertIn('agent_trace', result)
        self.assertTrue(result.get('ordered_nodes'))

    def test_teacher_suggestion_mock(self):
        result = run_teacher_suggestion({
            'classId': '1',
            'weakPointStats': [{'knowledgePoint': 'for 循环', 'count': 5}],
        })
        self.assertIn('classSummary', result)
        self.assertTrue(result['teachingSuggestions'])

    def test_agent_diagnose_legacy_compat(self):
        result = AgentOrchestrator.diagnose(None, {'code': 'print(1)', 'stderr': 'SyntaxError'})
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['weak_points'])

    def test_agent_backend_detects_crewai_or_mock(self):
        name = AgentOrchestrator.backend_name()
        self.assertIn(name, ('mock', 'crewai'))

    def test_agents_status(self):
        status = AgentOrchestrator.agents_status()
        self.assertEqual(len(status['agents']), 7)


if __name__ == '__main__':
    unittest.main()
