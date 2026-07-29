# -*- coding: utf-8 -*-
"""知识图谱：Python 初学者静态拓扑 + 学情驱动节点状态。"""
from collections import Counter, defaultdict

from app.data.kg_topology import KG_EDGES, KG_NODES
from app.data.knowledge_node_registry import kg_id_from_key
from app.models import StudentMistake, TrialQuestion, TrialQuestionProgress, User, db
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
    def _empty_stats() -> dict:
        return {
            'answered': 0,
            'correct': 0,
            'wrong': 0,
            'fail_count': 0,
            'error_types': Counter(),
        }

    @staticmethod
    def _node_id_for_key(knowledge_key: str | None) -> str:
        key = (knowledge_key or '').lower()
        return KNOWLEDGE_KEY_TO_NODE.get(key, kg_id_from_key(key) if key else KnowledgeGraphService._default_node_id())

    @staticmethod
    def _node_stats(user_id: int) -> dict[str, dict]:
        stats: dict[str, dict] = defaultdict(KnowledgeGraphService._empty_stats)
        rows = TrialQuestionProgress.query.filter(
            TrialQuestionProgress.user_id == user_id,
            TrialQuestionProgress.status == 'completed',
        ).all()
        for row in rows:
            question = db.session.get(TrialQuestion, row.question_id)
            key = (question.knowledge_key if question else None) or 'var'
            node_id = KnowledgeGraphService._node_id_for_key(key)
            bucket = stats[node_id]
            bucket['answered'] += 1
            if row.is_correct:
                bucket['correct'] += 1
            else:
                bucket['wrong'] += 1
        for item in MistakeService.list_weak_knowledge(user_id, limit=20):
            node_id = KnowledgeGraphService._node_id_for_key(item['knowledge_key'])
            stats[node_id]['fail_count'] = max(stats[node_id]['fail_count'], item.get('fail_count', 0))

        active_mistakes = [
            row for row in StudentMistake.query.filter_by(user_id=user_id).all()
            if MistakeService._is_active(row)
        ]
        for row in active_mistakes:
            node_id = KnowledgeGraphService._node_id_for_key(row.knowledge_key)
            bucket = stats[node_id]
            bucket['fail_count'] = max(bucket['fail_count'], row.fail_count or 1)
            if row.error_type:
                bucket['error_types'][row.error_type] += row.fail_count or 1
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
    def _node_metrics(bucket: dict | None, affected_student_count: int = 0) -> dict:
        bucket = bucket or KnowledgeGraphService._empty_stats()
        answered = int(bucket.get('answered') or 0)
        correct = int(bucket.get('correct') or 0)
        wrong = int(bucket.get('wrong') or max(0, answered - correct))
        fail_count = int(bucket.get('fail_count') or 0)
        accuracy = round(correct / answered * 100) if answered else None
        accuracy_penalty = max(0, 60 - accuracy) if accuracy is not None else 0
        weak_score = fail_count * 2 + wrong + affected_student_count * 3 + accuracy_penalty
        errors = bucket.get('error_types') or Counter()
        if isinstance(errors, Counter):
            top_error_types = [
                {'error_type': key, 'count': count}
                for key, count in errors.most_common(3)
            ]
        else:
            top_error_types = []
        return {
            'answered_count': answered,
            'correct_count': correct,
            'wrong_count': wrong,
            'accuracy': accuracy,
            'fail_count': fail_count,
            'weak_score': round(weak_score, 2),
            'affected_student_count': affected_student_count,
            'top_error_types': top_error_types,
        }

    @staticmethod
    def _summary_from_nodes(nodes: list[dict], student_count: int) -> dict:
        ranked = sorted(
            [node for node in nodes if (node.get('weak_score') or 0) > 0],
            key=lambda item: (-(item.get('weak_score') or 0), -(item.get('affected_student_count') or 0)),
        )
        top = [
            {
                'id': node['id'],
                'label': node['label'],
                'status': node.get('status'),
                'weak_score': node.get('weak_score') or 0,
                'fail_count': node.get('fail_count') or 0,
                'wrong_count': node.get('wrong_count') or 0,
                'accuracy': node.get('accuracy'),
                'affected_student_count': node.get('affected_student_count') or 0,
            }
            for node in ranked[:5]
        ]
        return {
            'top_weak_nodes': top,
            'student_count': student_count,
            'total_mistakes': sum(node.get('fail_count') or 0 for node in nodes),
            'max_weak_score': max([node.get('weak_score') or 0 for node in nodes] or [0]),
        }

    @staticmethod
    def get_student_graph(user_id: int) -> dict:
        stats = KnowledgeGraphService._node_stats(user_id)
        recommended_ids = set()
        if db.session.get(User, user_id):
            from app.services.recommendation import RecommendationService

            rec = RecommendationService.get_student_recommendations(user_id, '7d')
            for weak in rec.get('weak_knowledge') or []:
                node_id = KnowledgeGraphService._node_id_for_key(weak['knowledge_key'])
                recommended_ids.add(node_id)
        nodes = []
        base_nodes, base_edges = _topology()
        for base in base_nodes:
            bucket = stats.get(base['id'])
            accuracy = (
                round(bucket['correct'] / bucket['answered'] * 100)
                if bucket and bucket.get('answered')
                else None
            )
            is_personal_weak = bool(
                bucket and (
                    (bucket.get('fail_count') or 0) > 0
                    or (bucket.get('wrong') or 0) > 0
                    or (accuracy is not None and accuracy < 60)
                )
            )
            metrics = KnowledgeGraphService._node_metrics(bucket, 1 if is_personal_weak else 0)
            nodes.append({
                **base,
                'status': KnowledgeGraphService._resolve_status(base['id'], stats, recommended_ids),
                **metrics,
            })
        return {
            'nodes': nodes,
            'edges': base_edges,
            'scope': 'student',
            'user_id': user_id,
            'graph_backend': graph_backend_name(),
            'summary': KnowledgeGraphService._summary_from_nodes(nodes, 1 if db.session.get(User, user_id) else 0),
            'recommended_node_ids': sorted(recommended_ids),
        }

    @staticmethod
    def get_class_graph(class_id: int) -> dict:
        students = User.query.filter_by(class_id=class_id).all()
        weak_counter: Counter[str] = Counter()
        mastery_counter: Counter[str] = Counter()
        aggregate: dict[str, dict] = defaultdict(KnowledgeGraphService._empty_stats)
        affected_students: dict[str, set[int]] = defaultdict(set)
        for student in students:
            stats = KnowledgeGraphService._node_stats(student.id)
            for node_id, bucket in stats.items():
                aggregate[node_id]['answered'] += bucket.get('answered') or 0
                aggregate[node_id]['correct'] += bucket.get('correct') or 0
                aggregate[node_id]['wrong'] += bucket.get('wrong') or 0
                aggregate[node_id]['fail_count'] += bucket.get('fail_count') or 0
                aggregate[node_id]['error_types'].update(bucket.get('error_types') or Counter())
                is_weak = (
                    bucket['fail_count'] >= 2
                    or (bucket['answered'] >= 1 and bucket['correct'] / bucket['answered'] < 0.4)
                )
                if is_weak:
                    weak_counter[node_id] += 1
                    affected_students[node_id].add(student.id)
                if bucket['answered'] >= 2 and bucket['correct'] / bucket['answered'] >= 0.8:
                    mastery_counter[node_id] += 1
        total = max(len(students), 1)
        nodes = []
        base_nodes, base_edges = _topology()
        for base in base_nodes:
            weak_ratio = weak_counter[base['id']] / total
            master_ratio = mastery_counter[base['id']] / total
            metrics = KnowledgeGraphService._node_metrics(
                aggregate.get(base['id']),
                len(affected_students.get(base['id'], set())),
            )
            not_mastered_percent = round(len(affected_students.get(base['id'], set())) / total * 100)
            if weak_ratio >= 0.1 or metrics['fail_count'] >= 3 or metrics['weak_score'] >= 10:
                status = 'weak'
            elif master_ratio >= 0.5:
                status = 'mastered'
            elif weak_counter[base['id']] > 0 or mastery_counter[base['id']] > 0:
                status = 'learning'
            else:
                status = 'unlearned'
            nodes.append({
                **base,
                'status': status,
                'weak_count': weak_counter[base['id']],
                'student_count': total,
                'not_mastered_percent': not_mastered_percent,
                **metrics,
            })
        return {
            'nodes': nodes,
            'edges': base_edges,
            'scope': 'class',
            'class_id': class_id,
            'student_count': len(students),
            'summary': KnowledgeGraphService._summary_from_nodes(nodes, len(students)),
        }

    @staticmethod
    def get_node_affected_students(class_id: int, node_id: str) -> dict:
        from app.models import Class

        class_obj = db.session.get(Class, class_id)
        class_name = class_obj.name if class_obj else None
        students = User.query.filter_by(class_id=class_id).all()
        items = []
        for student in students:
            stats = KnowledgeGraphService._node_stats(student.id)
            bucket = stats.get(node_id)
            if not bucket:
                continue
            answered = bucket.get('answered') or 0
            correct = bucket.get('correct') or 0
            is_weak = (
                (bucket.get('fail_count') or 0) >= 2
                or (answered >= 1 and correct / answered < 0.4)
            )
            if not is_weak:
                continue
            error_types = [
                {'error_type': key, 'count': count}
                for key, count in (bucket.get('error_types') or Counter()).most_common(3)
            ]
            if not error_types and (bucket.get('wrong') or 0) > 0:
                error_types = [{'error_type': 'wrong_answer', 'count': bucket.get('wrong') or 1}]
            items.append(
                {
                    'id': student.id,
                    'username': student.username,
                    'real_name': student.real_name or student.username,
                    'class_id': class_id,
                    'class_name': class_name,
                    'fail_count': bucket.get('fail_count') or 0,
                    'wrong_count': bucket.get('wrong') or 0,
                    'error_types': error_types,
                }
            )
        items.sort(key=lambda row: (-(row.get('fail_count') or 0), row.get('username') or ''))
        return {
            'class_id': class_id,
            'class_name': class_name,
            'node_id': node_id,
            'items': items,
            'total': len(items),
        }

    @staticmethod
    def get_admin_graph() -> dict:
        base_nodes, base_edges = _topology()
        nodes = [{**base, 'status': 'unlearned'} for base in base_nodes]
        return {'nodes': nodes, 'edges': base_edges, 'scope': 'admin'}
