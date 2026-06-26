# -*- coding: utf-8 -*-
"""诊断引擎的核心数据结构与枚举定义。

设计目标：
- 用四层错因模型（语法 / 规则 / 逻辑 / 迁移）替代原先粗粒度的 errorType；
- 区分「不会」与「会但写错」，输出可解释的判别依据；
- 给出结构化的补救策略，便于前端显性化展示与行动。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---- 错因层级 ----
# syntax  语法层：漏冒号、缩进错误、变量拼写错误
# rule    规则层：不理解 range(1, 5) 不含 5、索引从 0 开始
# logic   逻辑层：循环条件不更新形成死循环、逻辑顺序写反
# transfer 迁移层：会写求和，但不会写最大值遍历；照抄模板不会改
ERROR_LAYERS = ('syntax', 'rule', 'logic', 'transfer')

ERROR_LAYER_LABELS = {
    'syntax': '语法层',
    'rule': '规则层',
    'logic': '逻辑层',
    'transfer': '迁移层',
    'none': '已掌握',
}

# ---- 掌握度判别 ----
# cannot        尚未掌握：概念未建立
# can_but_wrong 会但写错：理解大致思路，细节不稳
# transfer_gap  会但不会迁移：基础题会，变式迁移失败
# mastered      本次作答正确
PROFICIENCY_LEVELS = ('cannot', 'can_but_wrong', 'transfer_gap', 'mastered')

PROFICIENCY_LABELS = {
    'cannot': '尚未掌握',
    'can_but_wrong': '会但写错',
    'transfer_gap': '会但不会迁移',
    'mastered': '已掌握',
}

# ---- 补救策略 ----
STRATEGY_TYPES = (
    'trace_variables',   # 展示变量变化过程（while/for 逐步推演）
    'micro_fix',         # 生成微型修复题（改 1-2 行即可验证）
    'concept_explain',   # 概念澄清（如 range 左闭右开）
    'pattern_compare',   # 对照已会题型（求和 -> 最大值迁移）
    'syntax_checklist',  # 语法层检查清单
    'consolidate',       # 巩固同类题型（作答正确时）
)

STRATEGY_LABELS = {
    'trace_variables': '展示变量变化过程',
    'micro_fix': '生成微型修复题',
    'concept_explain': '概念澄清',
    'pattern_compare': '对照已会题型',
    'syntax_checklist': '语法检查清单',
    'consolidate': '巩固同类题型',
}


@dataclass
class KnowledgePoint:
    """关联知识点 + 当前掌握度。"""

    node: str
    mastery: str = 'unknown'  # unlearned | learning | weak | mastered | unknown
    reason: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {'node': self.node, 'mastery': self.mastery, 'reason': self.reason}


@dataclass
class RemediationStrategy:
    """结构化补救策略，前端据此渲染分步引导。"""

    type: str = 'micro_fix'
    title: str = ''
    detail: str = ''
    steps: list[str] = field(default_factory=list)
    micro_exercise: str = ''

    def __post_init__(self) -> None:
        if not self.title:
            self.title = STRATEGY_LABELS.get(self.type, self.type)

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': self.type,
            'title': self.title,
            'detail': self.detail,
            'steps': list(self.steps),
            'microExercise': self.micro_exercise,
        }


@dataclass
class DiagnosisContext:
    """诊断输入：从前端 / orchestrator 注入的全部信号。"""

    code: str = ''
    stdin: str = ''
    stdout: str = ''
    stderr: str = ''
    expected_output: str = ''
    error_message: str = ''
    knowledge_points: list[str] = field(default_factory=list)
    attempt_count: int = 1
    answer_status: str = 'wrong'  # correct | wrong | partial
    question_requirements: str = ''
    recent_mistakes: list[Any] = field(default_factory=list)
    knowledge_mastery: list[dict] = field(default_factory=list)
    conversation_history: list[Any] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict) -> 'DiagnosisContext':
        def pick(*keys: str, default: Any = '') -> Any:
            for key in keys:
                if key in payload and payload[key] is not None:
                    return payload[key]
            return default

        return cls(
            code=str(pick('code', default='')),
            stdin=str(pick('stdin', 'input', default='')),
            stdout=str(pick('stdout', default='')),
            stderr=str(pick('stderr', default='')),
            expected_output=str(pick('expectedOutput', 'expected_output', default='')),
            error_message=str(pick('errorMessage', 'error_message', 'stderr', default='')),
            knowledge_points=list(pick('knowledgePoints', 'knowledge_points', default=[]) or []),
            attempt_count=int(pick('attemptCount', 'attempt_count', default=1) or 1),
            answer_status=str(pick('answerStatus', 'answer_status', default='wrong')),
            question_requirements=str(
                pick('questionRequirements', 'questionPrompt', 'questionTitle', default='')
            ),
            recent_mistakes=list(pick('recentMistakes', 'recent_mistakes', default=[]) or []),
            knowledge_mastery=list(pick('knowledgeMastery', 'knowledge_mastery', default=[]) or []),
            conversation_history=list(pick('conversationHistory', 'conversation_history', default=[]) or []),
        )

    @property
    def lowered_blob(self) -> str:
        """代码 + 错误信息的小写合并文本，便于关键词匹配。"""
        return f'{self.code}\n{self.error_message}\n{self.stderr}'.lower()

    @property
    def output_mismatch(self) -> bool:
        """有预期输出且与实际输出不一致（且非运行报错）。"""
        if not self.expected_output:
            return False
        if self.stderr.strip():
            return False
        return self.expected_output.strip() != self.stdout.strip()


@dataclass
class DiagnosisResult:
    """诊断输出：四层错因 + 掌握判别 + 策略。"""

    error_layer: str = 'logic'
    error_subtype: str = 'unknown'
    diagnosis: str = ''
    confidence: float = 0.8
    proficiency: str = 'cannot'
    proficiency_reason: str = ''
    related_knowledge: list[KnowledgePoint] = field(default_factory=list)
    weak_points: list[str] = field(default_factory=list)
    strategy: RemediationStrategy = field(default_factory=RemediationStrategy)
    evidence: list[str] = field(default_factory=list)

    @property
    def error_layer_label(self) -> str:
        return ERROR_LAYER_LABELS.get(self.error_layer, self.error_layer)

    @property
    def proficiency_label(self) -> str:
        return PROFICIENCY_LABELS.get(self.proficiency, self.proficiency)

    def to_dict(self) -> dict[str, Any]:
        """完整诊断结构（含旧字段，向后兼容前端旧消费者）。"""
        return {
            # ---- 新增结构化字段 ----
            'errorLayer': self.error_layer,
            'errorLayerLabel': self.error_layer_label,
            'errorSubtype': self.error_subtype,
            'proficiency': self.proficiency,
            'proficiencyLabel': self.proficiency_label,
            'proficiencyReason': self.proficiency_reason,
            'relatedKnowledgePoints': [kp.to_dict() for kp in self.related_knowledge],
            'remediationStrategy': self.strategy.to_dict(),
            'evidence': list(self.evidence),
            # ---- 兼容旧字段 ----
            'errorType': _legacy_error_type(self.error_layer),
            'weakPoints': list(self.weak_points),
            'diagnosis': self.diagnosis,
            'confidence': round(float(self.confidence), 2),
        }


_LEGACY_ERROR_TYPE_MAP = {
    'syntax': 'syntax',
    'rule': 'concept',
    'logic': 'logic',
    'transfer': 'concept',
    'none': 'unknown',
}


def _legacy_error_type(error_layer: str) -> str:
    """把四层模型映射回旧的 errorType，保证旧前端不 break。"""
    return _LEGACY_ERROR_TYPE_MAP.get(error_layer, 'unknown')
