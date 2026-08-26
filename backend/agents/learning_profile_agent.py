"""Learning profile analyst with strict output validation.

优先 DeepSeek/OpenAI 兼容端点；未配置或失败时回退讯飞星火；
两者都不可用时返回 local_rules 交由规则抽取兜底。
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.services.iflytek_spark import IflytekSparkService

ALLOWED_DIMENSIONS = {
    'knowledge_foundation', 'mistake_pattern', 'learning_goal',
    'learning_pace', 'explanation_preference', 'cognitive_state',
    'major_background', 'interest_direction',
}


class DimensionResult(BaseModel):
    value: str = Field(min_length=1, max_length=300)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list, max_length=4)


class ProfileAnalysis(BaseModel):
    dimensions: dict[str, DimensionResult] = Field(default_factory=dict)


class LearningProfileAgent:
    ROLE = 'Python learning profile analyst'
    GOAL = 'Summarize only evidence-backed, non-sensitive learning signals into learning dimensions.'
    SYSTEM_PROMPT = 'You are a careful educational analyst.'

    @classmethod
    def _prompt(cls, context: dict) -> str:
        return (
            'Return JSON only: {"dimensions": {key: {"value": string, "confidence": 0..1, '
            '"evidence": [string]}}}. Allowed keys: knowledge_foundation,mistake_pattern,'
            'learning_goal,learning_pace,explanation_preference,cognitive_state,'
            'major_background,interest_direction. '
            'Values must be concise Chinese summaries (<=40 chars), not the raw sentence. '
            'Only include keys the student message provides evidence for. '
            'Do not infer identity, health, or sensitive traits. cognitive_state must be a neutral learning '
            'state such as stable, needs_support, or frustration_risk with evidence.\n'
            f'Approved learning context: {context}'
        )

    @classmethod
    def _recalibration_prompt(cls, context: dict, required_keys: set[str]) -> str:
        required = ','.join(sorted(required_keys))
        return (
            'Return JSON only: {"dimensions": {key: {"value": string, "confidence": 0..1, '
            '"evidence": [string]}}}. '
            f'Mandatory keys: {required}. '
            'The selected_changes are explicit student-confirmed preferences. Preserve their intent, '
            'rewrite them only into concise Chinese profile summaries (<=40 chars), and include every '
            'mandatory key. You may include another allowed dimension only when the supplied context '
            'contains direct evidence. Do not infer identity, health, or sensitive traits. '
            f'Approved recalibration context: {context}'
        )

    @staticmethod
    def _normalize(raw: object, evidence_label: str) -> dict | None:
        """校验并规整模型返回；结构非法时返回 None。"""
        candidate = raw.get('dimensions') if isinstance(raw, dict) and 'dimensions' in raw else raw
        if not isinstance(candidate, dict):
            return None
        normalized = {}
        for key, value in candidate.items():
            if key not in ALLOWED_DIMENSIONS:
                continue
            normalized[key] = value if isinstance(value, dict) else {
                'value': str(value), 'confidence': 0.75, 'evidence': [evidence_label],
            }
        try:
            parsed = ProfileAnalysis.model_validate({'dimensions': normalized})
        except ValidationError:
            return None
        changes = {}
        for key, item in parsed.dimensions.items():
            changes[key] = {
                'value': item.value,
                'confidence': round(item.confidence, 2),
                'evidence': [e[:160] for e in item.evidence] or [evidence_label],
                'source': 'mixed',
            }
        return changes or None

    @classmethod
    def analyze(cls, context: dict, *, timeout_seconds: float | None = None) -> tuple[dict, str]:
        prompt = cls._prompt(context)
        spark_timeout = float(timeout_seconds) if timeout_seconds is not None else 30.0
        llm_timeout = float(timeout_seconds) if timeout_seconds is not None else 25.0

        try:
            from flask import current_app, has_app_context

            if has_app_context() and current_app.config.get('TESTING'):
                return {}, 'local_rules'
        except Exception:
            pass

        try:
            from agents.llm_client import chat_json as llm_chat_json

            raw = llm_chat_json(
                system=cls.SYSTEM_PROMPT,
                user=prompt,
                timeout=max(3.0, min(llm_timeout, 25.0)),
                max_tokens=640,
            )
            changes = cls._normalize(raw, '大模型学习画像分析') if raw else None
            if changes:
                return changes, 'llm'
        except Exception:
            pass

        if IflytekSparkService.configured():
            try:
                raw = IflytekSparkService.chat_json(
                    cls.SYSTEM_PROMPT,
                    prompt,
                    timeout=max(3.0, min(spark_timeout, 30.0)),
                )
                changes = cls._normalize(raw, '讯飞星火学习画像分析')
                if changes:
                    return changes, 'spark'
            except Exception:
                pass

        return {}, 'local_rules'

    @classmethod
    def recalibrate(
        cls,
        context: dict,
        required_keys: set[str],
        *,
        timeout_seconds: float = 12.0,
    ) -> tuple[dict, str]:
        """Require a validated real-provider result for explicit profile calibration."""
        prompt = cls._recalibration_prompt(context, required_keys)
        required = {key for key in required_keys if key in ALLOWED_DIMENSIONS}

        try:
            from flask import current_app, has_app_context

            if has_app_context() and current_app.config.get('TESTING'):
                return {}, 'local_rules'
        except Exception:
            pass

        try:
            from agents.llm_client import chat_json as llm_chat_json

            raw = llm_chat_json(
                system=cls.SYSTEM_PROMPT,
                user=prompt,
                timeout=max(3.0, min(float(timeout_seconds), 15.0)),
                max_tokens=720,
                force_json_object=True,
            )
            changes = cls._normalize(raw, '大模型画像校准') if raw else None
            if changes and required.issubset(changes):
                return changes, 'llm'
        except Exception:
            pass

        if IflytekSparkService.configured():
            try:
                raw = IflytekSparkService.chat_json(
                    cls.SYSTEM_PROMPT,
                    prompt,
                    timeout=max(3.0, min(float(timeout_seconds), 15.0)),
                )
                changes = cls._normalize(raw, '讯飞星火画像校准')
                if changes and required.issubset(changes):
                    return changes, 'spark'
            except Exception:
                pass

        return {}, 'local_rules'
