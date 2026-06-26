# -*- coding: utf-8 -*-
"""学习诊断智能体 LearningDiagnosisAgent。

职责升级：从“按异常名映射粗粒度 errorType”升级为四层错因模型
（语法 / 规则 / 逻辑 / 迁移）+「不会 vs 会但写错」判别 + 结构化补救策略。
具体诊断逻辑下沉到 ``agents.diagnosis`` 引擎，本模块只做薄封装与字段适配。
"""

from .diagnosis import DiagnosisContext, diagnose

ROLE = 'Python 初学者学习诊断专家'
GOAL = '区分学生是“不会”还是“会但写错”，定位四层错因并给出可解释的诊断与策略'
BACKSTORY = (
    '你长期辅导 Python 零基础学生，擅长从代码、运行日志、历史错误与知识掌握度中，'
    '判断错误属于语法、规则、逻辑还是迁移层，并区分概念未建立与细节失误，从不说打击性语言。'
)


def execute(payload: dict) -> dict:
    """返回结构化诊断结果（含向后兼容的 errorType / weakPoints 字段）。"""
    ctx = DiagnosisContext.from_payload(payload)
    result = diagnose(ctx)
    return result.to_dict()
