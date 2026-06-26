# -*- coding: utf-8 -*-
"""知识诊断引擎：四层错因模型 + 掌握度判别。

对外暴露 ``diagnose`` 入口与核心数据结构，供 ``learning_diagnosis_agent``
及下游 code_analysis / knowledge_graph / feedback 智能体复用。
"""

from .engine import diagnose
from .schema import (
    ERROR_LAYERS,
    PROFICIENCY_LEVELS,
    STRATEGY_TYPES,
    DiagnosisContext,
    DiagnosisResult,
    KnowledgePoint,
    RemediationStrategy,
)

__all__ = [
    'diagnose',
    'DiagnosisContext',
    'DiagnosisResult',
    'KnowledgePoint',
    'RemediationStrategy',
    'ERROR_LAYERS',
    'PROFICIENCY_LEVELS',
    'STRATEGY_TYPES',
]
