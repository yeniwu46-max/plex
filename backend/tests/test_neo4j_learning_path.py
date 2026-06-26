# -*- coding: utf-8 -*-
import unittest

from app.services.neo4j_client import InMemoryGraphStore, get_graph_store, graph_backend_name


class Neo4jClientTests(unittest.TestCase):
    def test_memory_store_topology(self):
        store = InMemoryGraphStore()
        topo = store.get_topology()
        self.assertGreater(len(topo['nodes']), 10)
        self.assertGreater(len(topo['edges']), 5)
        prereq = store.get_prerequisites('loop')
        self.assertTrue(len(prereq) >= 1)

    def test_get_graph_store_fallback(self):
        store = get_graph_store()
        self.assertTrue(store.is_available())
        self.assertIn(graph_backend_name(), ('memory', 'neo4j'))
