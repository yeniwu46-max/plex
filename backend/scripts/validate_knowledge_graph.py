"""Static graph integrity gate for the 990 knowledge-graph requirement."""
from __future__ import annotations

import json
from pathlib import Path

from app.data.kg_topology import KG_EDGES, KG_NODES, KG_NODE_IDS

REQUIRED_RELATION_TYPES = {'belongs_to', 'prerequisite', 'assesses', 'error', 'remediation', 'resource', 'mastery', 'transfer'}


def validate() -> dict:
    ids = [node['id'] for node in KG_NODES]
    duplicate_nodes = sorted({item for item in ids if ids.count(item) > 1})
    signatures = [(edge['source'], edge['target'], edge['type']) for edge in KG_EDGES]
    duplicate_edges = sorted({item for item in signatures if signatures.count(item) > 1})
    invalid_edges = [edge for edge in KG_EDGES if edge['source'] not in KG_NODE_IDS or edge['target'] not in KG_NODE_IDS]
    incoming = {node_id: 0 for node_id in KG_NODE_IDS}
    outgoing = {node_id: 0 for node_id in KG_NODE_IDS}
    for edge in KG_EDGES:
        if edge['source'] in outgoing and edge['target'] in incoming:
            outgoing[edge['source']] += 1
            incoming[edge['target']] += 1
    isolated = sorted(node_id for node_id in KG_NODE_IDS if not incoming[node_id] and not outgoing[node_id])

    # Cycle check only applies to prerequisite edges; related/path links are
    # intentionally allowed to form recommendation loops.
    adjacency = {node_id: [] for node_id in KG_NODE_IDS}
    for edge in KG_EDGES:
        if edge['type'] == 'prerequisite':
            adjacency[edge['source']].append(edge['target'])
    visiting, visited, cycle = set(), set(), []
    def walk(node):
        if node in visiting:
            cycle.append(node)
            return True
        if node in visited:
            return False
        visiting.add(node)
        found = any(walk(target) for target in adjacency[node])
        visiting.remove(node)
        visited.add(node)
        return found
    has_cycle = any(walk(node) for node in KG_NODE_IDS)
    relation_types = {edge['type'] for edge in KG_EDGES}
    missing_relation_types = sorted(REQUIRED_RELATION_TYPES - relation_types)
    return {
        'status': 'passed' if not duplicate_nodes and not duplicate_edges and not invalid_edges and not isolated and not has_cycle and not missing_relation_types else 'failed',
        'node_count': len(ids), 'edge_count': len(signatures),
        'duplicate_nodes': duplicate_nodes, 'duplicate_edges': duplicate_edges,
        'invalid_edges': invalid_edges, 'isolated_nodes': isolated,
        'prerequisite_cycle': has_cycle, 'cycle_nodes': cycle,
        'relation_types': sorted(relation_types), 'missing_relation_types': missing_relation_types,
    }


def main():
    report = validate()
    path = Path(__file__).resolve().parents[1] / 'reports' / 'iflytek-990-kg-validation-20260828.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
