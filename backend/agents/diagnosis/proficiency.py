# -*- coding: utf-8 -*-
"""掌握度判别器：区分「不会」「会但写错」「会但不会迁移」。

输入信号：
- 当前命中的错因层级（error_layer）；
- attemptCount（本题尝试次数）；
- KG 节点掌握度快照（knowledge_mastery）；
- 结构化历史错因（recent_mistakes，含 error_layer）；
- analyzer 信号（迁移层启发式）。
"""

from __future__ import annotations

from typing import Any

from .schema import DiagnosisContext

_MASTERED = {'mastered'}
_WEAK = {'weak', 'learning'}


def _mastery_lookup(ctx: DiagnosisContext) -> dict[str, str]:
    """把 knowledge_mastery 列表整理成 {节点名: 状态}。"""
    table: dict[str, str] = {}
    for item in ctx.knowledge_mastery or []:
        if isinstance(item, dict):
            name = item.get('name') or item.get('node') or item.get('id') or item.get('title')
            status = item.get('status') or item.get('mastery') or 'unknown'
            if name:
                table[str(name)] = str(status)
    return table


def _node_mastery(table: dict[str, str], nodes: list[str]) -> str:
    """取关联节点中“最高”的掌握状态，用于判断是否已掌握。"""
    best = 'unknown'
    order = {'unknown': 0, 'unlearned': 0, 'learning': 1, 'weak': 1, 'recommended': 1, 'mastered': 2}
    for node in nodes:
        st = table.get(node, 'unknown')
        if order.get(st, 0) > order.get(best, 0):
            best = st
    return best


def _history_same_layer(ctx: DiagnosisContext, layer: str) -> int:
    """历史错因中与当前同层级的出现次数。"""
    count = 0
    for m in ctx.recent_mistakes or []:
        if isinstance(m, dict):
            meta = m.get('meta') if isinstance(m.get('meta'), dict) else m
            hist_layer = (
                m.get('error_layer')
                or m.get('errorLayer')
                or (meta.get('error_layer') if isinstance(meta, dict) else None)
            )
            if hist_layer == layer:
                count += m.get('fail_count', 1) if isinstance(m.get('fail_count'), int) else 1
    return count


def judge(ctx: DiagnosisContext, error_layer: str, related_nodes: list[str], signals: dict) -> dict:
    """返回 {proficiency, reason} 判别结果。"""
    if ctx.answer_status == 'correct':
        return {'proficiency': 'mastered', 'reason': '本次作答正确，关联知识点掌握稳定。'}

    table = _mastery_lookup(ctx)
    node_state = _node_mastery(table, related_nodes)
    same_layer_history = _history_same_layer(ctx, error_layer)
    attempt = ctx.attempt_count

    # 迁移层直接命中：会基础但变式迁移失败
    if error_layer == 'transfer' or signals.get('transfer_gap'):
        return {
            'proficiency': 'transfer_gap',
            'reason': '相似基础题型已掌握，但本题的变式迁移尚未完成。',
        }

    # 语法层 + 首次尝试：多为概念 / 习惯尚未建立
    if error_layer == 'syntax':
        if attempt <= 1 and node_state not in _MASTERED:
            return {
                'proficiency': 'cannot',
                'reason': '出现语法层错误且为首次尝试，基础语法习惯尚未建立。',
            }
        return {
            'proficiency': 'can_but_wrong',
            'reason': '思路基本成形，主要卡在语法细节（如冒号 / 缩进 / 拼写）。',
        }

    # 关联节点已 mastered，却仍在同类出错 -> 会但写错
    if node_state in _MASTERED:
        return {
            'proficiency': 'can_but_wrong',
            'reason': f'关联知识点此前已达「掌握」，但在{error_layer}细节上反复出错。',
        }

    # 多次尝试 + 同层历史多次 -> 会但写错（细节不稳）
    if attempt >= 3 or same_layer_history >= 2:
        return {
            'proficiency': 'can_but_wrong',
            'reason': '已多次尝试且同类错误反复出现，理解大致到位但细节不稳定。',
        }

    # 关联节点偏弱 / 未学 -> 尚未掌握
    if node_state in _WEAK or node_state in ('unlearned', 'unknown'):
        return {
            'proficiency': 'cannot',
            'reason': '关联知识点掌握度偏弱，相关概念尚未真正建立。',
        }

    return {
        'proficiency': 'cannot',
        'reason': '当前证据更倾向于概念理解不足，建议从基础推演入手。',
    }


def detect_transfer_gap(ctx: DiagnosisContext, signals: dict) -> bool:
    """迁移层启发式：基础遍历题已 mastered，但本题换了目标却写不出。

    判据（任一）：
    - KG 中「累加求和 / for 循环」已 mastered，本题涉及「最大值 / 查找」且输出不符；
    - 代码里出现求和骨架（+=）但题目要求是最大值 / 比较，结构没迁移。
    """
    table = _mastery_lookup(ctx)
    base_mastered = any(
        table.get(n) == 'mastered' for n in ('累加求和', 'for 循环', 'range')
    )
    text = (ctx.question_requirements + ' ' + ' '.join(ctx.knowledge_points)).lower()
    blob = text + ' ' + ctx.code.lower()
    wants_transfer = any(k in blob for k in ('最大', '最小', 'max', 'min', '查找', 'search', '排序', 'sort'))

    if base_mastered and wants_transfer and ctx.output_mismatch:
        return True

    # 代码里只有累加骨架，但题目要的是比较 / 最值
    has_sum_skeleton = '+=' in ctx.code or 'sum' in ctx.code.lower()
    needs_compare = any(k in text for k in ('最大', '最小', 'max', 'min'))
    has_compare = any(op in ctx.code for op in ('>', '<')) or 'max(' in ctx.code or 'min(' in ctx.code
    if has_sum_skeleton and needs_compare and not has_compare and ctx.output_mismatch:
        return True
    return False
