# -*- coding: utf-8 -*-
import unittest

from app.data.knowledge_node_registry import (
    kg_id_from_key,
    kg_id_from_star_path,
    get_entry,
    KNOWLEDGE_NODE_REGISTRY,
)


class KnowledgeNodeRegistryTests(unittest.TestCase):
    def test_star_path_mapping(self):
        self.assertEqual(kg_id_from_star_path('stage1-intro'), 'intro')
        self.assertEqual(kg_id_from_star_path('stage2-loop'), 'loop')

    def test_key_mapping(self):
        self.assertEqual(kg_id_from_key('input'), 'io')
        self.assertEqual(kg_id_from_key('unknown-x', 'var'), 'var')

    def test_registry_entries_unique(self):
        kg_ids = [e.kg_id for e in KNOWLEDGE_NODE_REGISTRY]
        self.assertEqual(len(kg_ids), len(set(kg_ids)))
        star_ids = [e.star_path_id for e in KNOWLEDGE_NODE_REGISTRY if e.star_path_id]
        self.assertEqual(len(star_ids), len(set(star_ids)))

    def test_get_entry(self):
        entry = get_entry('var')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.domain_key, 'data-vars')
