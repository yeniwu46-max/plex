# -*- coding: utf-8 -*-
"""Neo4j 客户端：知识图谱拓扑读写，不可用时回退内存图。"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from app.data.kg_topology import KG_EDGES, KG_NODES


class InMemoryGraphStore:
    """Neo4j 不可用时的内存图回退。"""

    def __init__(self) -> None:
        self._nodes = {n['id']: dict(n) for n in KG_NODES}
        self._edges = [dict(e) for e in KG_EDGES]
        self._prereq: dict[str, list[str]] = defaultdict(list)
        for edge in self._edges:
            if edge.get('type') == 'prerequisite':
                self._prereq[edge['target']].append(edge['source'])

    def is_available(self) -> bool:
        return True

    def get_topology(self) -> dict[str, Any]:
        return {'nodes': list(self._nodes.values()), 'edges': self._edges, 'source': 'memory'}

    def get_prerequisites(self, node_id: str) -> list[str]:
        return list(self._prereq.get(node_id, []))

    def get_all_prerequisite_map(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self._prereq.items()}


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._fallback = InMemoryGraphStore()

    def close(self) -> None:
        self._driver.close()

    def is_available(self) -> bool:
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def get_topology(self) -> dict[str, Any]:
        if not self.is_available():
            return self._fallback.get_topology()
        query = """
        MATCH (n:KnowledgeNode)
        OPTIONAL MATCH (a:KnowledgeNode)-[r]->(b:KnowledgeNode)
        RETURN collect(DISTINCT n) AS nodes, collect(DISTINCT r) AS rels
        """
        with self._driver.session() as session:
            record = session.run(query).single()
        if not record or not record['nodes']:
            return self._fallback.get_topology()
        nodes = []
        for node in record['nodes']:
            props = dict(node)
            nodes.append({
                'id': props.get('id'),
                'label': props.get('label'),
                'domain': props.get('domain'),
                'level': props.get('level'),
                'description': props.get('description'),
                'x': props.get('x'),
                'y': props.get('y'),
                'star_path_id': props.get('star_path_id'),
                'document_id': props.get('document_id'),
            })
        edges = []
        for rel in record['rels'] or []:
            if rel is None:
                continue
            edges.append({
                'id': rel.element_id,
                'source': rel.start_node.get('id'),
                'target': rel.end_node.get('id'),
                'type': rel.type.lower(),
                'label': dict(rel).get('label', rel.type),
            })
        return {'nodes': nodes, 'edges': edges, 'source': 'neo4j'}

    def get_prerequisites(self, node_id: str) -> list[str]:
        if not self.is_available():
            return self._fallback.get_prerequisites(node_id)
        query = """
        MATCH (pre:KnowledgeNode)-[:PREREQUISITE]->(n:KnowledgeNode {id: $id})
        RETURN pre.id AS id
        """
        with self._driver.session() as session:
            rows = session.run(query, id=node_id)
            result = [row['id'] for row in rows]
        # Neo4j 未播种前置边时回退内存拓扑，避免路径锁定失效
        return result or self._fallback.get_prerequisites(node_id)

    def get_all_prerequisite_map(self) -> dict[str, list[str]]:
        if not self.is_available():
            return self._fallback.get_all_prerequisite_map()
        query = """
        MATCH (pre:KnowledgeNode)-[:PREREQUISITE]->(n:KnowledgeNode)
        RETURN n.id AS target, collect(pre.id) AS sources
        """
        result: dict[str, list[str]] = defaultdict(list)
        with self._driver.session() as session:
            for row in session.run(query):
                result[row['target']] = list(row['sources'])
        if not result:
            return self._fallback.get_all_prerequisite_map()
        return dict(result)


_store: Neo4jGraphStore | InMemoryGraphStore | None = None


def _enabled() -> bool:
    return os.getenv('NEO4J_ENABLED', 'false').lower() in ('1', 'true', 'yes')


def get_graph_store() -> Neo4jGraphStore | InMemoryGraphStore:
    global _store
    # 单元测试强制内存图，避免本机 Neo4j 未播种前置边导致路径锁定断言漂移
    try:
        from flask import current_app, has_app_context

        if has_app_context() and current_app.config.get('TESTING'):
            if not isinstance(_store, InMemoryGraphStore):
                _store = InMemoryGraphStore()
            return _store
    except Exception:
        pass
    if _store is not None:
        return _store
    if _enabled():
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'plex-neo4j-dev')
        try:
            store = Neo4jGraphStore(uri, user, password)
            if store.is_available():
                _store = store
                return _store
        except Exception:
            pass
    _store = InMemoryGraphStore()
    return _store


def graph_backend_name() -> str:
    store = get_graph_store()
    if isinstance(store, Neo4jGraphStore) and store.is_available():
        return 'neo4j'
    return 'memory'
