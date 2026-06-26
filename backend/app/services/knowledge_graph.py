# -*- coding: utf-8 -*-
"""知识图谱：Python 初学者静态拓扑 + 学情驱动节点状态。"""
from collections import Counter, defaultdict

from app.data.kg_topology import KG_EDGES, KG_NODES
from app.data.knowledge_node_registry import kg_id_from_key
from app.models import TrialQuestion, TrialQuestionProgress, User, db
from app.services.mistake import MistakeService
from app.services.neo4j_client import get_graph_store, graph_backend_name

KNOWLEDGE_KEY_TO_NODE = {
    'intro': 'intro',
    'comment': 'comment',
    'python': 'intro',
    'lang': 'intro',
    'syntax': 'var',
    'basic': 'var',
    'var': 'var',
    'io': 'io',
    'input': 'io',
    'ops': 'ops',
    'cond': 'cond',
    'condition': 'cond',
    'loop': 'loop',
    'range': 'range',
    'list': 'list',
    'tuple': 'tuple',
    'set': 'tuple',
    'dict': 'dict',
    'str': 'str',
    'string': 'str',
    'func': 'func',
    'function': 'func',
    'file': 'file',
    'except': 'except',
    'exception': 'except',
    'algo': 'algo-sum',
    'algo-sum': 'algo-sum',
    'algo-search': 'algo-search',
    'algo-sort': 'algo-sort',
    'algo-dedup': 'algo-dedup',
    'nested': 'nested',
    'stage1': 'intro',
    'stage2': 'cond',
    'stage3': 'list',
    'stage4': 'algo-sum',
}


def _topology() -> tuple[list[dict], list[dict]]:
    topo = get_graph_store().get_topology()
    nodes = topo.get('nodes') or KG_NODES
    edges = topo.get('edges') or KG_EDGES
    return nodes, edges


class KnowledgeGraphService:
    @staticmethod
    def _default_node_id() -> str:
        return 'var'

    @staticmethod
    def _node_stats(user_id: int) -> dict[str, dict]:
        stats: dict[str, dict] = defaultdict(lambda: {'answered': 0, 'correct': 0, 'fail_count': 0})
        rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.user_id == user_id,
            TrialQuestionProgress.status == 'completed',
        ).all()
        default_node = KnowledgeGraphService._default_node_id()
        for row in rows:
            question = db.session.get(TrialQuestion, row.question_id)
            key = (question.knowledge_key if question else None) or 'var'
            node_id = KNOWLEDGE_KEY_TO_NODE.get(key.lower(), kg_id_from_key(key))
            bucket = stats[node_id]
            bucket['answered'] += 1
            if row.is_correct:
                bucket['correct'] += 1
        for item in MistakeService.list_weak_knowledge(user_id, limit=20):
            node_id = KNOWLEDGE_KEY_TO_NODE.get(item['knowledge_key'].lower(), default_node)
            stats[node_id]['fail_count'] = max(stats[node_id]['fail_count'], item.get('fail_count', 0))
        return stats

    @staticmethod
    def _resolve_status(node_id: str, stats: dict, recommended_ids: set[str]) -> str:
        bucket = stats.get(node_id, {'answered': 0, 'correct': 0, 'fail_count': 0})
        answered = bucket['answered']
        if node_id in recommended_ids:
            return 'recommended'
        if bucket['fail_count'] >= 2 or (answered >= 1 and answered and bucket['correct'] / answered < 0.4):
            return 'weak'
        if answered >= 2 and bucket['correct'] / answered >= 0.8:
            return 'mastered'
        if answered >= 1:
            return 'learning'
        return 'unlearned'

    @staticmethod
    def get_student_graph(user_id: int) -> dict:
        stats = KnowledgeGraphService._node_stats(user_id)
        recommended_ids = set()
        default_node = KnowledgeGraphService._default_node_id()
        if db.session.get(User, user_id):
            from app.services.recommendation import RecommendationService

            rec = RecommendationService.get_student_recommendations(user_id, '7d')
            for weak in rec.get('weak_knowledge') or []:
                node_id = KNOWLEDGE_KEY_TO_NODE.get(weak['knowledge_key'].lower(), default_node)
                recommended_ids.add(node_id)
        nodes = []
        base_nodes, base_edges = _topology()
        for base in base_nodes:
            nodes.append({
                **base,
                'status': KnowledgeGraphService._resolve_status(base['id'], stats, recommended_ids),
            })
        return {
            'nodes': nodes,
            'edges': base_edges,
            'scope': 'student',
            'user_id': user_id,
            'graph_backend': graph_backend_name(),
        }

    @staticmethod
    def get_class_graph(class_id: int) -> dict:
        students = User.query.filter_by(class_id=class_id).all()
        weak_counter: Counter[str] = Counter()
        mastery_counter: Counter[str] = Counter()
        for student in students:
            stats = KnowledgeGraphService._node_stats(student.id)
            for node_id, bucket in stats.items():
                if bucket['answered'] >= 1 and bucket['correct'] / bucket['answered'] < 0.4:
                    weak_counter[node_id] += 1
                if bucket['answered'] >= 2 and bucket['correct'] / bucket['answered'] >= 0.8:
                    mastery_counter[node_id] += 1
        total = max(len(students), 1)
        nodes = []
        base_nodes, base_edges = _topology()
        for base in base_nodes:
            weak_ratio = weak_counter[base['id']] / total
            master_ratio = mastery_counter[base['id']] / total
            if weak_ratio >= 0.35:
                status = 'weak'
            elif master_ratio >= 0.5:
                status = 'mastered'
            elif weak_counter[base['id']] > 0 or mastery_counter[base['id']] > 0:
                status = 'learning'
            else:
                status = 'unlearned'
            nodes.append({**base, 'status': status, 'weak_count': weak_counter[base['id']], 'student_count': total})
        return {
            'nodes': nodes,
            'edges': base_edges,
            'scope': 'class',
            'class_id': class_id,
            'student_count': len(students),
        }

    @staticmethod
    def get_admin_graph() -> dict:
        base_nodes, base_edges = _topology()
        nodes = [{**base, 'status': 'unlearned'} for base in base_nodes]
        return {'nodes': nodes, 'edges': base_edges, 'scope': 'admin'}
