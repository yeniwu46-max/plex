# -*- coding: utf-8 -*-
import unittest

from app import create_app
from app.data.kg_topology import KG_EDGES
from app.data.knowledge_node_registry import KNOWLEDGE_NODE_REGISTRY
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
        self.assertEqual(len(payload['nodes']), len(KNOWLEDGE_NODE_REGISTRY))
        self.assertGreaterEqual(len(payload['nodes']), 100)
        self.assertGreaterEqual(len(payload['edges']), 200)
        self.assertEqual(payload['scope'], 'admin')

    def test_graph_edges_are_unique_and_reference_known_nodes(self):
        node_ids = {entry.kg_id for entry in KNOWLEDGE_NODE_REGISTRY}
        signatures = {(edge['source'], edge['target'], edge['type']) for edge in KG_EDGES}
        self.assertEqual(len(signatures), len(KG_EDGES))
        self.assertTrue(all(edge['source'] in node_ids and edge['target'] in node_ids for edge in KG_EDGES))

    def test_student_graph_status_values(self):
        payload = KnowledgeGraphService.get_student_graph(999999)
        statuses = {node['status'] for node in payload['nodes']}
        self.assertTrue(statuses.issubset({'mastered', 'learning', 'weak', 'unlearned', 'recommended'}))


if __name__ == '__main__':
    unittest.main()
