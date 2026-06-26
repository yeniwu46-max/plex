# -*- coding: utf-8 -*-
"""诊断引擎主入口：analyzer -> rules -> proficiency -> strategy。"""

from __future__ import annotations

from . import analyzer as _analyzer
from . import proficiency as _proficiency
from .rules import RULES, Rule
from .schema import (
    DiagnosisContext,
    DiagnosisResult,
    KnowledgePoint,
    RemediationStrategy,
)

# 关联节点掌握度兜底来源（与 knowledge_scope 解耦，避免循环依赖）
try:
    from ..knowledge_scope import KEYWORD_TO_NODES, PYTHON_BEGINNER_NODES
except Exception:  # pragma: no cover - 兜底
    KEYWORD_TO_NODES = {}
    PYTHON_BEGINNER_NODES = []


def _mastery_table(ctx: DiagnosisContext) -> dict[str, str]:
    table: dict[str, str] = {}
    for item in ctx.knowledge_mastery or []:
        if isinstance(item, dict):
            name = item.get('name') or item.get('node') or item.get('id') or item.get('title')
            status = item.get('status') or item.get('mastery') or 'unknown'
            if name:
                table[str(name)] = str(status)
    return table


def _build_related(ctx: DiagnosisContext, rule_nodes: list[str]) -> list[KnowledgePoint]:
    table = _mastery_table(ctx)
    nodes: list[str] = []
    for n in [*rule_nodes, *ctx.knowledge_points]:
        if n and n not in nodes:
            nodes.append(n)
    result: list[KnowledgePoint] = []
    for node in nodes[:5]:
        mastery = table.get(node, 'unknown')
        reason = ''
        if mastery == 'mastered':
            reason = '此前已掌握，注意细节即可'
        elif mastery in ('weak', 'learning'):
            reason = '掌握度偏弱，建议优先巩固'
        elif mastery in ('unlearned', 'unknown'):
            reason = '相关概念可能尚未建立'
        result.append(KnowledgePoint(node=node, mastery=mastery, reason=reason))
    return result


_STRATEGY_TEMPLATES = {
    'syntax_checklist': {
        'detail': '按检查清单逐项核对语法，定位漏写或拼写问题。',
        'steps': [
            '检查每个 if/for/while/def 行尾是否有英文冒号。',
            '确认同一代码块缩进一致（统一 4 个空格）。',
            '核对变量名拼写在定义处与使用处是否完全一致。',
        ],
    },
    'concept_explain': {
        'detail': '先把规则说清楚，再用一个小例子验证理解。',
        'steps': [
            '用一句话复述这条规则（如 range 左闭右开）。',
            '写一个最小例子，手动算出预期结果。',
            '对照你的代码，找出与规则不一致的地方。',
        ],
    },
    'trace_variables': {
        'detail': '把变量在循环里的变化逐步写出来，让问题显形。',
        'steps': [
            '列一张表：循环每一轮记录关键变量的值。',
            '推演前 2-3 轮，观察变量是否按预期变化。',
            '定位第一处与预期不符的轮次，那里就是问题所在。',
        ],
    },
    'pattern_compare': {
        'detail': '把已会题型的骨架搬过来，只替换“每一步做的事”。',
        'steps': [
            '写出你已会题型（如求和）的遍历骨架。',
            '指出本题与它唯一不同的“每步操作”。',
            '在骨架上替换该操作，其余结构保持不变。',
        ],
    },
    'micro_fix': {
        'detail': '只改 1-2 行就能验证的小修复，快速建立正反馈。',
        'steps': [
            '定位最可疑的那一行。',
            '只改这一处，重新运行测试。',
            '观察输出变化，确认假设是否成立。',
        ],
    },
    'consolidate': {
        'detail': '作答正确，趁热做一道同类变式巩固。',
        'steps': [
            '回顾本题用到的核心结构。',
            '尝试一道稍难的同类变式。',
            '总结这一类题的通用解法。',
        ],
    },
}


def _build_strategy(rule: Rule | None, ctx: DiagnosisContext, related: list[KnowledgePoint]) -> RemediationStrategy:
    if ctx.answer_status == 'correct':
        stype = 'consolidate'
    else:
        stype = rule.strategy if rule else 'micro_fix'

    tmpl = _STRATEGY_TEMPLATES.get(stype, _STRATEGY_TEMPLATES['micro_fix'])
    focus = related[0].node if related else (rule.knowledge[0] if rule and rule.knowledge else '当前知识点')

    micro = ''
    if stype == 'micro_fix' or (rule and rule.strategy == 'trace_variables'):
        micro = f'在你的代码里，针对「{focus}」只改动 1-2 行后重新运行，看输出是否更接近预期。'
    elif stype == 'pattern_compare':
        micro = f'先写出 5 行以内的「{focus}」最小遍历示例，再迁移到本题。'
    elif stype == 'concept_explain':
        micro = f'写一个关于「{focus}」的 3 行小例子，手动算出结果并验证。'

    return RemediationStrategy(
        type=stype,
        detail=tmpl['detail'],
        steps=list(tmpl['steps']),
        micro_exercise=micro,
    )


def _match_rule(ctx: DiagnosisContext, signals: dict) -> Rule | None:
    for rule in RULES:
        try:
            if rule.match(ctx, signals):
                return rule
        except Exception:
            continue
    return None


def _fallback_rule(ctx: DiagnosisContext, signals: dict) -> Rule:
    """无规则命中时的兜底（逻辑层泛化）。"""
    knowledge = list(ctx.knowledge_points[:2]) or ['for 循环', 'range']
    return Rule(
        layer='logic', subtype='unresolved', priority=0,
        match=lambda c, s: True,
        knowledge=knowledge,
        confidence=0.6, strategy='trace_variables',
        summary='结果与预期不一致，但未匹配到明确错因。',
        cause='可能是边界条件、输出格式或中间逻辑与题目要求存在偏差。',
        fix='对照样例逐条检查输入输出，用 print 打印中间变量缩小范围。',
    )


def diagnose(ctx: DiagnosisContext) -> DiagnosisResult:
    """主诊断流程，返回结构化 DiagnosisResult。"""
    signals = _analyzer.analyze(ctx)
    # 迁移层启发式补充
    signals['transfer_gap'] = _proficiency.detect_transfer_gap(ctx, signals)

    # 作答正确：直接产出巩固型结果
    if ctx.answer_status == 'correct':
        related = _build_related(ctx, list(ctx.knowledge_points[:3]))
        strategy = _build_strategy(None, ctx, related)
        return DiagnosisResult(
            error_layer='none', error_subtype='none',
            diagnosis='本次作答正确，建议巩固同类题型并尝试稍难的变式。',
            confidence=0.92, proficiency='mastered',
            proficiency_reason='本次作答正确，关联知识点掌握稳定。',
            related_knowledge=related,
            weak_points=[kp.node for kp in related][:3],
            strategy=strategy,
            evidence=['answer_status:correct'],
        )

    rule = _match_rule(ctx, signals) or _fallback_rule(ctx, signals)
    related = _build_related(ctx, rule.knowledge)
    related_nodes = [kp.node for kp in related]

    prof = _proficiency.judge(ctx, rule.layer, related_nodes, signals)
    strategy = _build_strategy(rule, ctx, related)

    # 组织面向学生的诊断语句
    diagnosis_text = _compose_diagnosis(rule, prof, related_nodes)

    evidence = [rule.evidence_tag]
    for key in ('syntax_hint', 'while_no_update', 'off_by_one', 'name_typo',
                'transfer_gap', 'accumulator_use_before_init'):
        if signals.get(key):
            evidence.append(f'{key}={signals[key]}')

    return DiagnosisResult(
        error_layer=rule.layer,
        error_subtype=rule.subtype,
        diagnosis=diagnosis_text,
        confidence=rule.confidence,
        proficiency=prof['proficiency'],
        proficiency_reason=prof['reason'],
        related_knowledge=related,
        weak_points=related_nodes[:3] or list(rule.knowledge[:3]),
        strategy=strategy,
        evidence=evidence,
    )


def _compose_diagnosis(rule: Rule, prof: dict, related_nodes: list[str]) -> str:
    layer_label = {'syntax': '语法', 'rule': '规则', 'logic': '逻辑', 'transfer': '迁移'}.get(rule.layer, '')
    focus = '、'.join(related_nodes[:2]) if related_nodes else '相关知识点'
    return f'判定为{layer_label}层错误：{rule.summary} 关联「{focus}」。{rule.cause}'
