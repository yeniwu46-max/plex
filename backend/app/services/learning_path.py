# -*- coding: utf-8 -*-
"""学习路径服务：前置检查、拓扑排序、Next-Best-Action、资源与补救路径绑定。"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from app.data.knowledge_node_registry import (
    get_entry,
    kg_id_from_key,
    kg_id_from_star_path,
)
from app.models import PersonalizedLearningResource, StudentProfile, TrialQuestion, User, db
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.learning_adaptation import LearningAdaptationService
from app.services.neo4j_client import get_graph_store, graph_backend_name


STATUS_TO_SCORE = {
    'mastered': 0.92,
    'learning': 0.55,
    'weak': 0.28,
    'recommended': 0.35,
    'unlearned': 0.0,
}

from app.constants.test_accounts import is_test_sandbox_user
from app.constants.star_path_unlock import MASTERY_THRESHOLD, UNLOCK_ALL


class LearningPathService:
    @staticmethod
    def _mastery_map(user_id: int) -> dict[str, dict]:
        user = db.session.get(User, user_id)
        if is_test_sandbox_user(user):
            topology = get_graph_store().get_topology()
            mastered = STATUS_TO_SCORE['mastered']
            return {
                node['id']: {'status': 'mastered', 'mastery_score': mastered}
                for node in topology.get('nodes', [])
            }

        graph = KnowledgeGraphService.get_student_graph(user_id)
        result: dict[str, dict] = {}
        for node in graph.get('nodes', []):
            status = node.get('status', 'unlearned')
            result[node['id']] = {
                'status': status,
                'mastery_score': STATUS_TO_SCORE.get(status, 0.0),
            }
        return result

    @staticmethod
    def _prerequisite_map() -> dict[str, list[str]]:
        return get_graph_store().get_all_prerequisite_map()

    @staticmethod
    def _prerequisites_met(node_id: str, mastery: dict[str, dict], prereq_map: dict[str, list[str]]) -> bool:
        if UNLOCK_ALL:
            return True
        for pre in prereq_map.get(node_id, []):
            if mastery.get(pre, {}).get('mastery_score', 0) < MASTERY_THRESHOLD:
                return False
        return True

    @staticmethod
    def _topological_order(node_ids: list[str], prereq_map: dict[str, list[str]]) -> list[str]:
        indegree = {nid: 0 for nid in node_ids}
        children: dict[str, list[str]] = defaultdict(list)
        for target, sources in prereq_map.items():
            if target not in indegree:
                continue
            for src in sources:
                if src in indegree:
                    indegree[target] += 1
                    children[src].append(target)
        queue = deque([nid for nid, deg in indegree.items() if deg == 0])
        ordered: list[str] = []
        while queue:
            nid = queue.popleft()
            ordered.append(nid)
            for child in children.get(nid, []):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        for nid in node_ids:
            if nid not in ordered:
                ordered.append(nid)
        return ordered

    @staticmethod
    def _nba_score(
        node_id: str,
        mastery: dict[str, dict],
        focus_id: str | None,
        entry_level: str,
    ) -> float:
        score = mastery.get(node_id, {}).get('mastery_score', 0.0)
        gap = 1.0 - score
        focus_bonus = 0.15 if focus_id and node_id == focus_id else 0.0
        related_bonus = 0.08 if focus_id and focus_id in get_graph_store().get_prerequisites(node_id) else 0.0
        level_penalty = 0.05 if entry_level == 'intermediate' and score < 0.3 else 0.0
        return gap + focus_bonus + related_bonus - level_penalty

    @staticmethod
    def _bind_resources(user_id: int, kg_id: str) -> list[dict]:
        entry = get_entry(kg_id)
        keys = list(entry.knowledge_keys) if entry else [kg_id]
        resources = (
            PersonalizedLearningResource.query.filter(
                PersonalizedLearningResource.user_id == user_id,
                PersonalizedLearningResource.review_status == 'approved',
                PersonalizedLearningResource.knowledge_key.in_(keys),
            )
            .order_by(PersonalizedLearningResource.created_at.desc())
            .limit(3)
            .all()
        )
        profile = StudentProfile.query.filter_by(user_id=user_id).first()
        from app.services.recommendation import RecommendationService

        sorted_rows = RecommendationService.sort_personalized_resources(resources, profile)
        return [
            {
                'id': r.id,
                'type': r.resource_type,
                'title': r.title,
                'difficulty': r.difficulty,
                'knowledge_key': r.knowledge_key,
            }
            for r in sorted_rows[:3]
        ]

    @staticmethod
    def _bind_trials(kg_id: str) -> list[dict]:
        entry = get_entry(kg_id)
        keys = list(entry.knowledge_keys) if entry else [kg_id]
        rows = (
            TrialQuestion.query.filter(TrialQuestion.knowledge_key.in_(keys))
            .order_by(TrialQuestion.sort_order.asc())
            .limit(3)
            .all()
        )
        return [
            {
                'question_id': str(row.id),
                'title': (row.stem or '')[:80],
                'difficulty': row.coding_meta().get('difficulty', 1),
                'knowledge_key': row.knowledge_key,
            }
            for row in rows
        ]

    @staticmethod
    def _build_remediation_paths(user_id: int, mastery: dict[str, dict]) -> list[dict]:
        paths: list[dict] = []
        for item in LearningAdaptationService.active_for_student(user_id):
            key = item.get('knowledge_key') or 'python'
            kg_id = kg_id_from_key(key)
            plan = item.get('action_plan') or {}
            steps = [
                f'针对「{key}」执行 {plan.get("action", "visual_micro_practice")}',
                plan.get('recovery_rule', '完成补救练习后恢复常规难度'),
            ]
            paths.append({
                'trigger_node': kg_id,
                'steps': steps,
                'adaptation_id': item.get('id'),
                'knowledge_key': key,
            })
        return paths

    @staticmethod
    def _resolve_focus(focus: str | None) -> str | None:
        if not focus:
            return None
        if get_entry(focus):
            return focus
        star = kg_id_from_star_path(focus)
        if star:
            return star
        return kg_id_from_key(focus)

    @classmethod
    def plan(
        cls,
        user_id: int,
        focus_node_id: str | None = None,
        diagnosis_payload: dict | None = None,
    ) -> dict[str, Any]:
        topology = get_graph_store().get_topology()
        nodes_base = topology.get('nodes', [])
        node_ids = [n['id'] for n in nodes_base]
        mastery = cls._mastery_map(user_id)
        prereq_map = cls._prerequisite_map()
        focus_id = cls._resolve_focus(focus_node_id)
        if diagnosis_payload:
            weak = diagnosis_payload.get('weakPoints') or diagnosis_payload.get('weak_points') or []
            if weak and not focus_id:
                focus_id = kg_id_from_key(str(weak[0]))

        remediation_paths = cls._build_remediation_paths(user_id, mastery)

        # 星轨要把 26 个节点全部铺出来：既然已经取消解锁限制，学生可以任意跳转，
        # 路径就不该只列"还没掌握的"那几个（全掌握时原来只会剩 5 个兜底节点）。
        # 排序仍按推荐度来，_nba_score 以 1-掌握度 为主项，未掌握的自然排在前面；
        # 分数相同的按拓扑顺序（即教学顺序）稳定排列。
        ordered_candidates = cls._topological_order(node_ids, prereq_map)
        if focus_id and focus_id in node_ids:
            ordered_candidates = [focus_id] + [nid for nid in ordered_candidates if nid != focus_id]

        position = {nid: index for index, nid in enumerate(ordered_candidates)}
        scored = []
        for nid in ordered_candidates:
            entry = get_entry(nid)
            scored.append((cls._nba_score(nid, mastery, focus_id, entry.level if entry else 'basic'), nid))
        scored.sort(key=lambda item: (-item[0], position[item[1]]))
        ordered_ids = [nid for _, nid in scored] or node_ids

        ordered_nodes: list[dict] = []
        for index, nid in enumerate(ordered_ids):
            base = next((n for n in nodes_base if n['id'] == nid), {'id': nid, 'label': nid})
            entry = get_entry(nid)
            m = mastery.get(nid, {})
            prereqs_met = cls._prerequisites_met(nid, mastery, prereq_map)
            locked = not prereqs_met
            ordered_nodes.append({
                'id': nid,
                'star_path_id': entry.star_path_id if entry else base.get('star_path_id'),
                'label': base.get('label', entry.label if entry else nid),
                'order_index': index,
                'status': m.get('status', 'unlearned'),
                'mastery_score': m.get('mastery_score', 0.0),
                'locked': locked,
                'prerequisites_met': prereqs_met,
                'prerequisites': prereq_map.get(nid, []),
                'difficulty': entry.level if entry else base.get('level', 'basic'),
                'default_difficulty': entry.default_difficulty if entry else 1,
                'recommended_resources': cls._bind_resources(user_id, nid),
                'recommended_trials': cls._bind_trials(nid),
                'remediation': next(
                    (r for r in remediation_paths if r['trigger_node'] == nid),
                    None,
                ),
            })

        active_node = next(
            (n['id'] for n in ordered_nodes if not n['locked'] and n['mastery_score'] < MASTERY_THRESHOLD),
            ordered_nodes[0]['id'] if ordered_nodes else None,
        )
        active_entry = next((n for n in ordered_nodes if n['id'] == active_node), None)
        nba_reason = (
            f'前置已满足，掌握度 {int((active_entry or {}).get("mastery_score", 0) * 100)}%，'
            f'建议进入难度带 [0.4, 0.6]'
            if active_entry and active_entry.get('prerequisites_met')
            else '请先完成前置知识点再推进'
        )

        return {
            'ordered_nodes': ordered_nodes,
            'active_node_id': active_node,
            'next_best_action': {
                'node_id': active_node,
                'reason': nba_reason,
                'action': 'practice' if active_entry and not active_entry.get('locked') else 'review',
            },
            'remediation_paths': remediation_paths,
            'graph_backend': graph_backend_name(),
            'topology_source': topology.get('source', 'memory'),
        }

    @classmethod
    def ai_advice(cls, user_id: int, focus_node_id: str | None = None) -> dict:
        """调用 DeepSeek 生成小E 学习路径文字建议。"""
        from agents.http_client import direct_post
        from agents.llm_client import learning_path_provider

        plan = cls.plan(user_id, focus_node_id=focus_node_id)
        nodes = plan.get('ordered_nodes') or []
        weak = [n for n in nodes if (n.get('mastery_score') or 0) < 0.75][:6]
        strong = [n for n in nodes if (n.get('mastery_score') or 0) >= 0.75][:3]
        nba = plan.get('next_best_action') or {}

        def _fmt(items: list[dict]) -> str:
            return '、'.join(
                f"{item.get('label')}({int((item.get('mastery_score') or 0) * 100)}%)"
                for item in items
            ) or '暂无'

        fallback = {
            'advice': (
                f"建议优先巩固：{_fmt(weak)}。"
                f"当前下一步：{nba.get('reason') or '按星轨顺序推进'}。"
            ),
            'next_step': nba.get('reason') or '按推荐节点继续练习',
            'backend': 'local_rules',
            'fallback': True,
        }

        provider = learning_path_provider()
        if not provider:
            return fallback

        api_key, endpoint, model = provider
        system = (
            '你是 A3 学习系统的小E，为学生制定 Python 星轨学习路径建议。'
            '根据掌握度数据给出 2-3 句具体、可执行的建议，语气友好简洁。'
            '不要提及模型或 API。输出 JSON：{"advice":"...","next_step":"..."}'
        )
        user_msg = (
            f"薄弱节点：{_fmt(weak)}\n"
            f"已掌握：{_fmt(strong)}\n"
            f"系统推荐：{nba.get('reason') or '无'}"
        )
        try:
            response = direct_post(
                endpoint,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': system},
                        {'role': 'user', 'content': user_msg},
                    ],
                    'temperature': 0.45,
                    'max_tokens': 320,
                },
                timeout=(3, 12),
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            import json
            import re

            match = re.search(r'\{[\s\S]*\}', content)
            parsed = json.loads(match.group(0)) if match else {}
            advice = str(parsed.get('advice') or '').strip()
            next_step = str(parsed.get('next_step') or nba.get('reason') or '').strip()
            if not advice:
                return fallback
            return {
                'advice': advice,
                'next_step': next_step or advice[:80],
                'backend': 'deepseek',
                'fallback': False,
            }
        except Exception:
            return fallback
