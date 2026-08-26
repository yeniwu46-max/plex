# -*- coding: utf-8 -*-
import unittest

from app.data.knowledge_node_registry import (
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    get_entry,
    is_out_of_scope,
    kg_id_from_key,
    kg_id_from_star_path,
    nodes_for_domain,
    resolve_node_id,
)


class KnowledgeNodeRegistryTests(unittest.TestCase):
    def test_star_path_mapping(self):
        # 重构后星轨 id 与图谱 id 已统一
        self.assertEqual(kg_id_from_star_path('lang-print'), 'lang-print')
        self.assertEqual(kg_id_from_star_path('loop-for'), 'loop-for')

    def test_key_mapping(self):
        self.assertEqual(kg_id_from_key('input'), 'lang-input')
        self.assertEqual(kg_id_from_key('loop'), 'loop-for')
        self.assertEqual(kg_id_from_key('unknown-x', 'lang-var'), 'lang-var')

    def test_registry_entries_unique(self):
        kg_ids = [e.kg_id for e in KNOWLEDGE_NODE_REGISTRY]
        self.assertEqual(len(kg_ids), len(set(kg_ids)))
        star_ids = [e.star_path_id for e in KNOWLEDGE_NODE_REGISTRY if e.star_path_id]
        self.assertEqual(len(star_ids), len(set(star_ids)))

    def test_get_entry(self):
        entry = get_entry('lang-var')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.domain_key, 'lang-basics')

    def test_eight_domains_each_have_nodes(self):
        self.assertEqual(len(KNOWLEDGE_DOMAINS), 8)
        for domain in KNOWLEDGE_DOMAINS:
            self.assertTrue(nodes_for_domain(domain.key), f'{domain.key} 下没有知识点')

    def test_out_of_scope_keys_resolve_to_none(self):
        self.assertTrue(is_out_of_scope('dp'))
        self.assertIsNone(resolve_node_id('dp'))
        self.assertIsNone(resolve_node_id('完全不存在的key'))
