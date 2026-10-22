# -*- coding: utf-8 -*-
"""Read-only personalization, with one explicit source for ability evidence.

Eight profile dimensions retain self-description and preferences. In evidence
mode, legacy behavior claims are excluded and mastery/candidates/decisions come
from one versioned learner snapshot. Shadow mode preserves the legacy adapter.
Retrieval never creates a profile or changes ability state.
"""
from __future__ import annotations

from typing import Any

from flask import current_app

from app.data.knowledge_node_registry import resolve_node_id

from .schemas import LearnerContext

STATUS_TO_SCORE = {
    'mastered': 0.92,
    'learning': 0.55,
    'weak': 0.28,
    'recommended': 0.35,
    'unlearned': 0.0,
}

_PREFERENCE_KEYWORDS = {
    'concise': ('简洁', '直接', '精炼', '简短', '结论'),
    'detailed': ('详细', '循序', '展开', '完整', '深入'),
    'example_first': ('例子', '示例', '案例', '举例'),
    'visual': ('图', '可视', '表格', '画面'),
    'analogy': ('类比', '比喻', '生活'),
}


class LearnerContextService:
    @staticmethod
    def build(
        user_id: int | None,
        *,
        role: str = 'student',
        current_task: dict[str, Any] | None = None,
        include_mastery: bool = True,
        state_snapshot: dict[str, Any] | None = None,
    ) -> LearnerContext:
        ctx = LearnerContext(user_id=user_id, role=role, current_task=dict(current_task or {}))
        if not user_id or role != 'student':
            ctx.available = False
            return ctx
        if current_app.config.get('LEARNER_STATE_READ_MODE', 'shadow') == 'evidence':
            ctx.state_source = 'evidence'
        try:
            LearnerContextService._fill_profile(ctx)
        except Exception as exc:  # noqa: BLE001 - 画像缺失不应阻断检索
            current_app.logger.debug('learner profile unavailable: %s', exc)
        if include_mastery:
            try:
                LearnerContextService._fill_mastery(ctx, state_snapshot)
            except Exception as exc:  # noqa: BLE001
                current_app.logger.debug('learner mastery unavailable: %s', exc)
        try:
            if ctx.state_source != 'evidence':
                LearnerContextService._fill_mistakes(ctx)
        except Exception as exc:  # noqa: BLE001
            current_app.logger.debug('learner mistakes unavailable: %s', exc)
        return ctx

    @staticmethod
    def _fill_profile(ctx: LearnerContext) -> None:
        from app.models.student_profile import StudentProfile
        profile = StudentProfile.query.filter_by(user_id=ctx.user_id).first()
        if profile is None:
            return
        dimensions = profile.dimensions or {}
        values = {
            key: (value or {}).get('value')
            for key, value in dimensions.items()
            if isinstance(value, dict) and (value or {}).get('value')
            and not (ctx.state_source == 'evidence' and value.get('source') == 'behavior')
        }
        ctx.profile_dimensions = values
        ctx.explanation_preference = LearnerContextService._normalize_preference(values.get('explanation_preference'))
        ctx.learning_pace = str(values.get('learning_pace') or '')
        ctx.knowledge_foundation = str(values.get('knowledge_foundation') or '')
        ctx.mistake_pattern = str(values.get('mistake_pattern') or '')

    @staticmethod
    def _normalize_preference(raw: Any) -> str:
        text = str(raw or '').lower()
        if not text:
            return 'default'
        for key, keywords in _PREFERENCE_KEYWORDS.items():
            if key == text or any(k in text for k in keywords):
                return key
        return 'default'

    @staticmethod
    def _fill_mastery(ctx: LearnerContext, state_snapshot=None) -> None:
        if current_app.config.get('LEARNER_STATE_READ_MODE', 'shadow') == 'evidence':
            from app.services.learner_state import LearnerStateService
            snapshot = state_snapshot if state_snapshot is not None else LearnerStateService.snapshot(ctx.user_id)
            LearnerContextService._fill_evidence(ctx, snapshot)
            return
        from app.services.knowledge_graph import KnowledgeGraphService

        graph = KnowledgeGraphService.get_student_graph(ctx.user_id)
        for node in graph.get('nodes', []):
            status = node.get('status', 'unlearned')
            ctx.mastery[node['id']] = STATUS_TO_SCORE.get(status, 0.0)
            ctx.mastery_status[node['id']] = status
            if status == 'weak' and node['id'] not in ctx.weak_concepts:
                ctx.weak_concepts.append(node['id'])
        ctx.current_path = list(graph.get('recommended_node_ids') or [])

    @staticmethod
    def from_resource_snapshot(snapshot: dict) -> LearnerContext:
        """Internal only: no live profile, mode, graph scores or mistakes reads."""
        from copy import deepcopy
        ctx = LearnerContext(user_id=snapshot['user_id'], state_source=snapshot['state_source'],
                             current_task={'task_type': 'resource', 'concept_hint': snapshot['knowledge_key']})
        values = deepcopy(snapshot['profile'])
        ctx.profile_dimensions = values
        ctx.explanation_preference = LearnerContextService._normalize_preference(values.get('explanation_preference'))
        for name in ('learning_pace', 'knowledge_foundation', 'mistake_pattern'):
            setattr(ctx, name, str(values.get(name) or ''))
        if snapshot['state_source'] == 'evidence':
            LearnerContextService._fill_evidence(ctx, snapshot['learner_state'])
        return ctx

    @staticmethod
    def _fill_evidence(ctx: LearnerContext, snapshot: dict) -> None:
        from app.services.learner_decision import LearnerDecisionService
        ctx.state_source = 'evidence'
        ctx.state_version = snapshot['state_version']
        ctx.misconceptions = [{**item, 'concept_id': resolve_node_id(item['concept_id']) or item['concept_id']}
                             for item in snapshot.get('misconceptions', [])]
        ctx.learning_decision = LearnerDecisionService.from_snapshot(snapshot,
            focus_concept=ctx.current_task.get('concept_hint'))
        for item in snapshot['concepts']:
            cid = resolve_node_id(item['concept_id'])
            if not cid or item['estimate'] is None:
                continue
            score = item['estimate']
            ctx.mastery[cid] = score
            ctx.mastery_status[cid] = 'weak' if score < .4 else 'learning' if score < .75 else 'mastered'
            if score < .4:
                ctx.weak_concepts.append(cid)
        for change in snapshot['changes']:
            if change['kind'] == 'submission_graded' and '未通过' in change['reason']:
                ctx.recent_errors.append({'concept_id': resolve_node_id(change['concept_id']),
                    'question_title': change['question_title'], 'error_type': '正式判题未通过',
                    'evidence_id': change['event_id']})

    @staticmethod
    def _fill_mistakes(ctx: LearnerContext) -> None:
        from app.services.mistake import MistakeService

        for item in MistakeService.list_recent_with_meta(ctx.user_id, limit=6):
            concept_id = resolve_node_id(item.get('knowledge_key'))
            ctx.recent_errors.append(
                {
                    'concept_id': concept_id,
                    'knowledge_key': item.get('knowledge_key'),
                    'error_type': item.get('error_type'),
                    'error_layer': item.get('error_layer'),
                    'question_title': (item.get('question_title') or '')[:80],
                    'fail_count': item.get('fail_count'),
                }
            )
        for item in MistakeService.list_weak_knowledge(ctx.user_id, limit=5):
            concept_id = resolve_node_id(item.get('knowledge_key'))
            if concept_id and concept_id not in ctx.weak_concepts:
                ctx.weak_concepts.append(concept_id)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def mastery_band(score: float | None, thresholds: dict[str, float]) -> str:
        if score is None:
            return 'unknown'
        if score < float(thresholds.get('low', 0.4)):
            return 'low'
        if score < float(thresholds.get('high', 0.75)):
            return 'medium'
        return 'high'

    @staticmethod
    def summarize(ctx: LearnerContext, focus_ids: list[str], concept_names: dict[str, str]) -> str:
        """给 LLM 的学习者上下文（不含隐私字段，只含教学相关信息）。"""
        if not ctx.available:
            return '无学习者画像（游客或非学生角色）。'
        lines = []
        if ctx.state_source == 'evidence':
            lines.append(f'学习状态版本：{ctx.state_version}；分值为未校准的证据估计，未出现的概念尚待了解。')
        if ctx.knowledge_foundation:
            lines.append(f'知识基础自述（不作为测验成绩）：{ctx.knowledge_foundation[:80]}')
        if ctx.explanation_preference and ctx.explanation_preference != 'default':
            lines.append(f'讲解偏好：{ctx.profile_dimensions.get("explanation_preference", ctx.explanation_preference)}'[:100])
        if ctx.learning_pace:
            lines.append(f'学习节奏：{ctx.learning_pace[:60]}')
        if ctx.mistake_pattern:
            lines.append(f'自述或待核对的易错描述：{ctx.mistake_pattern[:80]}')
        focus_lines = []
        for cid in focus_ids:
            status = ctx.mastery_status.get(cid)
            if status:
                focus_lines.append(f'{concept_names.get(cid, cid)}：{status}（掌握度 {ctx.mastery.get(cid, 0):.2f}）')
        if focus_lines:
            lines.append('相关知识点掌握情况：' + '；'.join(focus_lines))
        if ctx.weak_concepts:
            lines.append('薄弱知识点：' + '、'.join(concept_names.get(c, c) for c in ctx.weak_concepts[:5]))
        if ctx.recent_errors:
            errs = [f'{e.get("question_title") or e.get("knowledge_key")}（{e.get("error_type") or "错误"}）' for e in ctx.recent_errors[:3]]
            lines.append('近期错题：' + '；'.join(errs))
        if ctx.learning_decision:
            lines.append('本次辅导依据：' + ctx.learning_decision['reason'])
            lines.append('建议核对动作：' + ctx.learning_decision['hint']['action'])
        task = ctx.current_task or {}
        if task.get('task_type'):
            lines.append(f'当前任务：{task.get("task_type")}' + (f' · {task.get("title")}' if task.get('title') else ''))
        return '\n'.join(lines) or '学习者画像尚在建立中。'
