"""Single-purpose Spark-backed learning profile analyst with strict output validation."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.services.iflytek_spark import IflytekSparkService

ALLOWED_DIMENSIONS = {
    'knowledge_foundation', 'mistake_pattern', 'learning_goal',
    'learning_pace', 'explanation_preference', 'cognitive_state',
}


class DimensionResult(BaseModel):
    value: str = Field(min_length=1, max_length=300)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list, max_length=4)


class ProfileAnalysis(BaseModel):
    dimensions: dict[str, DimensionResult] = Field(default_factory=dict)


class LearningProfileAgent:
    ROLE = 'Python learning profile analyst'
    GOAL = 'Summarize only evidence-backed, non-sensitive learning signals into six learning dimensions.'

    @classmethod
    def analyze(cls, context: dict) -> tuple[dict, str]:
        if not IflytekSparkService.configured():
            return {}, 'local_rules'
        prompt = (
            'Return JSON only: {"dimensions": {key: {"value": string, "confidence": 0..1, '
            '"evidence": [string]}}}. Allowed keys: knowledge_foundation,mistake_pattern,'
            'learning_goal,learning_pace,explanation_preference,cognitive_state. '
            'Do not infer identity, health, or sensitive traits. cognitive_state must be a neutral learning '
            'state such as stable, needs_support, or frustration_risk with evidence.\n'
            f'Approved learning context: {context}'
        )
        try:
            raw = IflytekSparkService.chat_json('You are a careful educational analyst.', prompt)
            # Spark Lite may return the dimensions object directly and may compress
            # each requested object to a string. Normalize only known keys before
            # the Pydantic contract validates the final shape.
            candidate = raw.get('dimensions') if isinstance(raw, dict) and 'dimensions' in raw else raw
            if not isinstance(candidate, dict):
                raise ValueError('profile dimensions must be an object')
            normalized = {}
            for key, value in candidate.items():
                if key not in ALLOWED_DIMENSIONS:
                    continue
                normalized[key] = value if isinstance(value, dict) else {
                    'value': str(value), 'confidence': 0.75, 'evidence': ['讯飞星火学习画像分析'],
                }
            parsed = ProfileAnalysis.model_validate({'dimensions': normalized})
        except (ValidationError, ValueError, TypeError):
            return {}, 'local_rules'
        changes = {}
        for key, item in parsed.dimensions.items():
            if key in ALLOWED_DIMENSIONS:
                changes[key] = {
                    'value': item.value,
                    'confidence': round(item.confidence, 2),
                    'evidence': [e[:160] for e in item.evidence],
                    'source': 'mixed',
                }
        return changes, 'spark'
