# -*- coding: utf-8 -*-
"""Learner Context：只读聚合已有学习者画像 / 掌握度 / 错题 / 当前任务。

- 画像来自 StudentProfileService（七维 + cognitive_state），不新建画像、不写入。
- 掌握度来自 KnowledgeGraphService.get_student_graph 的节点状态 → 分值（与 LearningPathService 口径一致）。
- 检索过程绝不修改画像；学习行为的反馈由 Learning Diagnosis Agent 负责。
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
    ) -> LearnerContext:
        ctx = LearnerContext(user_id=user_id, role=role, current_task=dict(current_task or {}))
        if not user_id or role != 'student':
            ctx.available = False
            return ctx
        try:
            LearnerContextService._fill_profile(ctx)
        except Exception as exc:  # noqa: BLE001 - 画像缺失不应阻断检索
            current_app.logger.debug('learner profile unavailable: %s', exc)
        if include_mastery:
            try:
                LearnerContextService._fill_mastery(ctx)
            except Exception as exc:  # noqa: BLE001
                current_app.logger.debug('learner mastery unavailable: %s', exc)
        try:
            LearnerContextService._fill_mistakes(ctx)
        except Exception as exc:  # noqa: BLE001
            current_app.logger.debug('learner mistakes unavailable: %s', exc)
        return ctx

    @staticmethod
    def _fill_profile(ctx: LearnerContext) -> None:
        from app.services.student_profile import StudentProfileService

        profile = StudentProfileService.get_or_create(ctx.user_id)
        dimensions = profile.dimensions or {}
        values = {
            key: (value or {}).get('value')
            for key, value in dimensions.items()
            if isinstance(value, dict) and (value or {}).get('value')
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
    def _fill_mastery(ctx: LearnerContext) -> None:
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
        if ctx.knowledge_foundation:
            lines.append(f'知识基础：{ctx.knowledge_foundation[:80]}')
        if ctx.explanation_preference and ctx.explanation_preference != 'default':
            lines.append(f'讲解偏好：{ctx.profile_dimensions.get("explanation_preference", ctx.explanation_preference)}'[:100])
        if ctx.learning_pace:
            lines.append(f'学习节奏：{ctx.learning_pace[:60]}')
        if ctx.mistake_pattern:
            lines.append(f'易错模式：{ctx.mistake_pattern[:80]}')
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
        task = ctx.current_task or {}
        if task.get('task_type'):
            lines.append(f'当前任务：{task.get("task_type")}' + (f' · {task.get("title")}' if task.get('title') else ''))
        return '\n'.join(lines) or '学习者画像尚在建立中。'
