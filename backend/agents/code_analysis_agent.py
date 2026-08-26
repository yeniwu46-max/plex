# -*- coding: utf-8 -*-
"""代码分析智能体 CodeAnalysisAgent。

优先消费学习诊断智能体的结构化结果（errorSubtype / evidence），
把四层错因翻译成初学者能懂的“问题 - 原因 - 修改方向”，避免与诊断引擎
重复维护规则。当被独立调用（旧端点 /agent/analyze-code）且无诊断结果时，
退化为基于 stderr / 代码的轻量规则。
"""

from .diagnosis.rules import RULES

ROLE = 'Python 初学者代码分析助教'
GOAL = '解释学生代码中的错误原因，给出修改方向，不直接给出完整答案'
BACKSTORY = (
    '你擅长把编译器与运行时的报错翻译成初学者能懂的语言，'
    '总是温和地指出问题并引导他们自己修正。'
)

# 由诊断规则库构建 subtype -> 解释 的查表，单一数据源。
_SUBTYPE_MAP = {
    rule.subtype: {
        'codeIssueSummary': rule.summary,
        'possibleCause': rule.cause,
        'fixDirection': rule.fix,
        'relatedConcepts': list(rule.knowledge),
    }
    for rule in RULES
}


def _from_diagnosis(diagnosis: dict) -> dict | None:
    subtype = diagnosis.get('errorSubtype')
    if subtype and subtype in _SUBTYPE_MAP:
        return dict(_SUBTYPE_MAP[subtype])
    return None


def _fallback(payload: dict) -> dict:
    stderr = (payload.get('stderr') or payload.get('errorMessage') or '').lower()
    code = payload.get('code', '')

    for rule in RULES:
        tag = rule.subtype
        # 仅用基于 stderr 的可独立判断的规则做兜底
        if tag == 'index_out_of_range' and 'indexerror' in stderr:
            return dict(_SUBTYPE_MAP[tag])
        if tag == 'name_undefined' and 'nameerror' in stderr:
            return dict(_SUBTYPE_MAP[tag])
        if tag == 'type_conversion' and ('typeerror' in stderr or 'valueerror' in stderr):
            return dict(_SUBTYPE_MAP[tag])
        if tag == 'zero_division' and 'zerodivisionerror' in stderr:
            return dict(_SUBTYPE_MAP[tag])
        if tag == 'syntax_generic' and ('syntaxerror' in stderr or 'indentationerror' in stderr):
            return dict(_SUBTYPE_MAP[tag])

    if stderr.strip():
        return {
            'codeIssueSummary': '程序运行未通过，输出或逻辑与预期不一致。',
            'possibleCause': stderr.strip()[:120],
            'fixDirection': '对照预期输出，用 print 打印中间变量，逐步缩小问题范围。',
            'relatedConcepts': ['变量', 'print 输出'],
        }
    if 'for' in code or 'while' in code:
        return {
            'codeIssueSummary': '循环逻辑可能未覆盖全部情况。',
            'possibleCause': '循环条件或 range 边界与题目要求不一致。',
            'fixDirection': '手动写出前三次循环的变量值，确认是否遗漏最后一次。',
            'relatedConcepts': ['for 循环', 'range'],
        }
    return {
        'codeIssueSummary': '代码结构基本可读，但结果仍未满足题目要求。',
        'possibleCause': '可能是边界条件或输出格式与样例不一致。',
        'fixDirection': '逐条对照样例输入输出，检查是否多输出了空格或换行。',
        'relatedConcepts': ['print 输出', '变量'],
    }


def execute(payload: dict) -> dict:
    diagnosis = payload.get('diagnosis')
    if isinstance(diagnosis, dict):
        if diagnosis.get('errorLayer') == 'none' or diagnosis.get('errorType') in {'none', 'correct'}:
            return {
                'codeIssueSummary': '代码运行结果符合预期，核心结构使用正确。',
                'possibleCause': '本次没有发现影响结果的代码问题。',
                'fixDirection': '保持当前写法，并尝试一道稍难的同类变式来巩固。',
                'relatedConcepts': diagnosis.get('weakPoints') or ['输出格式', '代码规范'],
            }
        from_diag = _from_diagnosis(diagnosis)
        if from_diag:
            return from_diag
    return _fallback(payload)
