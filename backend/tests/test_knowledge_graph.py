# -*- coding: utf-8 -*-
import unittest

from app import create_app
from app.services.knowledge_graph import KnowledgeGraphService


class KnowledgeGraphServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_admin_graph_has_nodes_and_edges(self):
        payload = KnowledgeGraphService.get_admin_graph()
        self.assertEqual(len(payload['nodes']), 20)
        self.assertGreaterEqual(len(payload['edges']), 10)
        self.assertEqual(payload['scope'], 'admin')

    def test_student_graph_status_values(self):
        payload = KnowledgeGraphService.get_student_graph(999999)
        statuses = {node['status'] for node in payload['nodes']}
        self.assertTrue(statuses.issubset({'mastered', 'learning', 'weak', 'unlearned', 'recommended'}))


if __name__ == '__main__':
    unittest.main()
