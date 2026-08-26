# -*- coding: utf-8 -*-
"""Python 初学者知识图谱静态拓扑（与 Neo4j / KnowledgeGraphService 共享）。

节点由 `knowledge_node_registry.KNOWLEDGE_NODE_REGISTRY` 派生，8 大类各占一列，
类内节点自上而下排布，因此图谱的横向就是教学推进方向。

边的语义：
- `prerequisite` 前置：类内相邻节点、以及跨类的主线推进。**注意** 2026-07-30 重排
  后前置边仅用于图谱上展示学习顺序建议，不再参与解锁判定（任意节点均可直接答题），
  见 app/constants/star_path_unlock.py 的 UNLOCK_ALL。
- `related` 相关：并列或互为补充的知识点。
- `path` 推荐路径：进阶延伸方向。
"""
from .knowledge_node_registry import (
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_NODE_REGISTRY,
    nodes_for_domain,
)

_COLUMN_X_START = 90
_COLUMN_X_STEP = 200
_ROW_Y_START = 120
_ROW_Y_STEP = 130


def _build_nodes() -> list[dict]:
    nodes: list[dict] = []
    for domain in KNOWLEDGE_DOMAINS:
        x = _COLUMN_X_START + (domain.order - 1) * _COLUMN_X_STEP
        for row, entry in enumerate(nodes_for_domain(domain.key)):
            nodes.append({
                'id': entry.kg_id,
                'label': entry.label,
                'domain': domain.title,
                'domain_key': domain.key,
                'level': entry.level,
                'description': entry.summary,
                'x': x,
                'y': _ROW_Y_START + row * _ROW_Y_STEP,
            })
    return nodes


KG_NODES = _build_nodes()


def _build_edges() -> list[dict]:
    edges: list[dict] = []
    seq = 0

    def add(source: str, target: str, edge_type: str, label: str) -> None:
        nonlocal seq
        seq += 1
        edges.append({'id': f'e{seq}', 'source': source, 'target': target, 'type': edge_type, 'label': label})

    # 类内串行：同一大类里前一个节点是后一个的前置
    for domain in KNOWLEDGE_DOMAINS:
        entries = nodes_for_domain(domain.key)
        for prev, current in zip(entries, entries[1:]):
            add(prev.kg_id, current.kg_id, 'prerequisite', '前置')

    # 跨类主线：每个大类的首个节点由上一大类的首个节点引出
    domain_heads = [nodes_for_domain(d.key)[0].kg_id for d in KNOWLEDGE_DOMAINS]
    for prev, current in zip(domain_heads, domain_heads[1:]):
        add(prev, current, 'prerequisite', '前置')

    # 跨类相关/推荐：把实际教学中互相依赖的点连起来
    add('loop-for', 'array-traverse', 'related', '相关')
    add('loop-nested', 'array-2d', 'related', '相关')
    add('loop-for', 'string-scan', 'related', '相关')
    add('array-basic', 'search-linear', 'prerequisite', '前置')
    add('array-traverse', 'search-stat', 'prerequisite', '前置')
    add('func-define', 'func-recursion', 'related', '相关')
    add('search-linear', 'search-binary', 'path', '推荐路径')
    add('search-sort', 'search-binary', 'path', '推荐路径')
    add('string-method', 'array-basic', 'related', '相关')
    add('branch-if', 'loop-while', 'related', '相关')
    return edges


KG_EDGES = _build_edges()

# 供外部快速判断某 id 是否为合法节点
KG_NODE_IDS = frozenset(node['id'] for node in KG_NODES)

assert len(KG_NODES) == len(KNOWLEDGE_NODE_REGISTRY)
