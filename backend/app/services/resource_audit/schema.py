"""Structured audit report schema."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

CheckLevel = Literal['PASS', 'WARNING', 'FAIL']
Verdict = Literal['PASS', 'NEED_MODIFY', 'REJECT']


@dataclass
class CheckItem:
    id: str
    label: str
    level: CheckLevel
    detail: str = ''

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StepResult:
    step: int
    name: str
    checks: list[CheckItem] = field(default_factory=list)
    score: int = 100
    summary: str = ''

    @property
    def has_fail(self) -> bool:
        return any(c.level == 'FAIL' for c in self.checks)

    @property
    def has_warning(self) -> bool:
        return any(c.level == 'WARNING' for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            'step': self.step,
            'name': self.name,
            'checks': [c.to_dict() for c in self.checks],
            'score': self.score,
            'summary': self.summary,
        }


@dataclass
class DimensionScores:
    knowledge_accuracy: int = 100
    teaching_quality: int = 100
    case_quality: int = 100
    exercise_quality: int = 100
    code_quality: int = 100
    ai_trustworthiness: int = 100

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    def min_score(self) -> int:
        values = list(asdict(self).values())
        return min(values) if values else 100


@dataclass
class AuditReport:
    verdict: Verdict
    suggested_publish: bool
    summary: str
    steps: list[StepResult]
    dimensions: DimensionScores
    knowledge_key: str = ''
    backend: str = 'sequential'
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'verdict': self.verdict,
            'suggested_publish': self.suggested_publish,
            'summary': self.summary,
            'steps': [s.to_dict() for s in self.steps],
            'dimensions': self.dimensions.to_dict(),
            'knowledge_key': self.knowledge_key,
            'backend': self.backend,
            'metadata': self.metadata,
        }

    def audit_risk_codes(self) -> list[str]:
        """Map FAIL checks to risk_reason codes for existing pipeline."""
        codes: list[str] = []
        for step in self.steps:
            for check in step.checks:
                if check.level == 'FAIL':
                    codes.append(f'audit_{check.id}')
        return list(dict.fromkeys(codes))
