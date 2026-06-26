# -*- coding: utf-8 -*-
"""将 PLEX 知识图谱种子写入 Neo4j。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / '.env')
load_dotenv(BACKEND_ROOT / '.env.spark.local', override=True)

from app.data.kg_topology import KG_EDGES, KG_NODES
from app.data.knowledge_node_registry import KNOWLEDGE_NODE_REGISTRY, get_entry

REL_TYPE_MAP = {
    'prerequisite': 'PREREQUISITE',
    'related': 'RELATED',
    'path': 'PATH',
    'advanced': 'ADVANCED',
}


def seed() -> None:
    from neo4j import GraphDatabase

    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'plex-neo4j-dev')
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()

    with driver.session() as session:
        session.run('MATCH (n:KnowledgeNode) DETACH DELETE n')
        for base in KG_NODES:
            entry = get_entry(base['id'])
            session.run(
                """
                CREATE (n:KnowledgeNode {
                    id: $id, label: $label, domain: $domain, level: $level,
                    description: $description, x: $x, y: $y,
                    star_path_id: $star_path_id, document_id: $document_id
                })
                """,
                id=base['id'],
                label=base['label'],
                domain=base['domain'],
                level=base['level'],
                description=base.get('description'),
                x=base.get('x'),
                y=base.get('y'),
                star_path_id=entry.star_path_id if entry else None,
                document_id=entry.document_id if entry else None,
            )
        for edge in KG_EDGES:
            rel_type = REL_TYPE_MAP.get(edge['type'], 'RELATED')
            session.run(
                f"""
                MATCH (a:KnowledgeNode {{id: $source}}), (b:KnowledgeNode {{id: $target}})
                CREATE (a)-[r:{rel_type} {{label: $label}}]->(b)
                """,
                source=edge['source'],
                target=edge['target'],
                label=edge.get('label', rel_type),
            )
    driver.close()
    print(f'neo4j seeded: {len(KG_NODES)} nodes, {len(KG_EDGES)} edges, registry={len(KNOWLEDGE_NODE_REGISTRY)}')


if __name__ == '__main__':
    seed()
