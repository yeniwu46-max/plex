# -*- coding: utf-8 -*-
"""Educational Strategy Layer：根据掌握度 / 意图 / 错误 / 任务场景选择教学策略与提示等级。

阈值与映射全部来自 strategy.json。练习场景的 Hint Level 在此进入 Answer Policy，而不是仅由前端控制。
"""
from __future__ import annotations

from typing import Any

from .learner_context_service import LearnerContextService
from .schemas import GraphContext, LearnerContext, QueryUnderstanding, TeachingStrategy
from .settings import strategy_config

STRATEGIES = (
    'DIRECT_EXPLANATION',
    'SCAFFOLDING',
    'SOCRATIC_GUIDANCE',
    'MISCONCEPTION_CORRECTION',
    'EXAMPLE_BASED',
    'PRACTICE_RECOMMENDATION',
    'PREREQUISITE_REMEDIATION',
    'EXTENSION',
)

STRATEGY_LABELS = {
    'DIRECT_EXPLANATION': '直接讲解',
    'SCAFFOLDING': '脚手架引导',
    'SOCRATIC_GUIDANCE': '苏格拉底式提问',
    'MISCONCEPTION_CORRECTION': '误区纠正',
    'EXAMPLE_BASED': '示例驱动',
    'PRACTICE_RECOMMENDATION': '练习推荐',
    'PREREQUISITE_REMEDIATION': '前置补救',
    'EXTENSION': '拓展延伸',
}

_STRATEGY_INSTRUCTIONS = {
    'DIRECT_EXPLANATION': '直接、清晰地讲解概念，先给结论再解释原因。',
    'SCAFFOLDING': '把问题拆成小步骤，每步只给必要的支撑，鼓励学生自己完成下一步。',
    'SOCRATIC_GUIDANCE': '多用反问和引导性问题，让学生自己推导出答案，不要直接给结论。',
    'MISCONCEPTION_CORRECTION': '先指出学生可能持有的误区并解释为什么错，再给出正确理解。',
    'EXAMPLE_BASED': '先给一个简短、贴近场景的代码或生活示例，再抽象出规律。',
    'PRACTICE_RECOMMENDATION': '在讲解后推荐 1-2 个匹配当前水平的练习方向，说明练习目的。',
    'PREREQUISITE_REMEDIATION': '发现前置知识未掌握时，先用两三句补齐前置概念，再回到当前问题。',
    'EXTENSION': '在掌握良好的基础上给出进一步的思考方向、更优写法或真实应用。',
}


class StrategyService:
    @staticmethod
    def select(
        understanding: QueryUnderstanding,
        learner: LearnerContext | None,
        graph: GraphContext,
        *,
        requested_hint_level: int | None = None,
    ) -> TeachingStrategy:
        cfg = strategy_config()
        thresholds = cfg.get('mastery_thresholds', {'low': 0.4, 'high': 0.75})
        max_strategies = int(cfg.get('max_strategies', 3))
        ts = TeachingStrategy()

        # 1) 掌握度区间
        focus_mastery: float | None = None
        if learner and learner.available and graph.focus_ids:
            known = [learner.mastery[c] for c in graph.focus_ids if c in learner.mastery]
            focus_mastery = min(known) if known else 0.0
        ts.focus_mastery = focus_mastery
        ts.mastery_band = LearnerContextService.mastery_band(focus_mastery, thresholds)

        picked: list[str] = []

        def add(items: list[str], why: str) -> None:
            for item in items:
                if item in STRATEGIES and item not in picked:
                    picked.append(item)
                    ts.rationale.append(f'{STRATEGY_LABELS.get(item, item)}：{why}')

        # 2) 前置缺口优先
        if graph.unmet_prerequisites and ts.mastery_band == 'low':
            add(['PREREQUISITE_REMEDIATION'], f'存在未掌握的前置知识 {len(graph.unmet_prerequisites)} 个')

        # 3) 错误 / 迷思
        if understanding.intent == 'debug_error' or understanding.error_type or (
            learner and any(e.get('concept_id') in graph.focus_ids for e in learner.recent_errors)
        ):
            add(cfg.get('misconception_boost', ['MISCONCEPTION_CORRECTION']), '问题涉及报错或近期错题相关知识点')

        # 4) 意图映射
        add(cfg.get('strategy_by_intent', {}).get(understanding.intent, []), f'问题意图为 {understanding.intent}')

        # 5) 掌握度映射
        band_key = ts.mastery_band if ts.mastery_band in {'low', 'medium', 'high'} else 'medium'
        add(cfg.get('strategy_by_mastery', {}).get(band_key, []), f'知识点掌握度处于 {band_key} 区间')

        if not picked:
            add(['DIRECT_EXPLANATION'], '默认策略')
        ts.strategies = picked[:max_strategies]

        # 6) 表达风格（画像 explanation_preference）
        pref_map = cfg.get('explanation_preference_map', {})
        pref = learner.explanation_preference if learner else 'default'
        ts.style = pref_map.get(pref) or pref_map.get('default', '')

        # 7) 练习场景 Hint Policy
        task = (learner.current_task if learner else {}) or {}
        task_type = str(task.get('task_type') or '').lower()
        practice_scenes = set(cfg.get('hint_policy', {}).get('practice_scenes', []))
        ts.practice_mode = task_type in practice_scenes
        if ts.practice_mode:
            StrategyService._apply_hint_policy(ts, cfg.get('hint_policy', {}), requested_hint_level or task.get('hint_level'))
        return ts

    @staticmethod
    def _apply_hint_policy(ts: TeachingStrategy, policy: dict[str, Any], requested: Any) -> None:
        levels = policy.get('levels', {})
        band_key = ts.mastery_band if ts.mastery_band in {'low', 'medium', 'high'} else 'medium'
        max_level = int(policy.get('max_level_by_mastery', {}).get(band_key, 3))
        try:
            level = int(requested) if requested is not None else int(policy.get('default_level', 1))
        except (TypeError, ValueError):
            level = int(policy.get('default_level', 1))
        level = max(1, min(level, max_level, 4))
        spec = levels.get(str(level), {})
        ts.hint_level = level
        ts.hint_max_level = max_level
        ts.hint_policy = {
            'level': level,
            'max_level': max_level,
            'name': spec.get('name', f'Level {level}'),
            'allow_code': bool(spec.get('allow_code', False)),
            'allow_solution': bool(spec.get('allow_solution', False)),
            'instruction': spec.get('instruction', ''),
        }
        # 练习场景下策略偏向引导而非直接讲解
        if not ts.hint_policy['allow_solution']:
            ts.strategies = [s for s in ts.strategies if s != 'DIRECT_EXPLANATION'] or ['SCAFFOLDING']
            if 'SOCRATIC_GUIDANCE' not in ts.strategies and len(ts.strategies) < 3:
                ts.strategies.append('SOCRATIC_GUIDANCE')
            ts.rationale.append(f'练习场景提示等级 {level}/{max_level}，禁止直接给出答案')

    @staticmethod
    def instructions(ts: TeachingStrategy) -> str:
        lines = [f'- {STRATEGY_LABELS.get(s, s)}：{_STRATEGY_INSTRUCTIONS.get(s, "")}' for s in ts.strategies]
        if ts.style:
            lines.append(f'- 表达风格：{ts.style}')
        return '\n'.join(lines)

    @staticmethod
    def public_view(ts: TeachingStrategy) -> dict[str, Any]:
        """返回给前端的教学策略视图（含中文标签）。"""
        return {
            'strategies': [{'code': s, 'label': STRATEGY_LABELS.get(s, s)} for s in ts.strategies],
            'mastery_band': ts.mastery_band,
            'style': ts.style,
            'practice_mode': ts.practice_mode,
            'hint_level': ts.hint_level,
            'hint_max_level': ts.hint_max_level,
            'hint_name': ts.hint_policy.get('name') if ts.hint_policy else None,
        }
