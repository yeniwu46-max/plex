# -*- coding: utf-8 -*-
"""知识图谱智能体 KnowledgeGraphAgent。

优先消费学习诊断智能体输出的 relatedKnowledgePoints（含真实掌握度），
据此定位相关节点、前置知识与复习建议；缺失时退化为关键词匹配。
"""

from .knowledge_scope import KEYWORD_TO_NODES, PREREQUISITE_MAP, PYTHON_BEGINNER_NODES

ROLE = 'Python 初学者知识图谱导航员'
GOAL = '根据错误与薄弱点定位相关节点、前置知识与复习建议'
BACKSTORY = (
    '你熟悉 PLEX 面向零基础学生的 Python 知识图谱，'
    '只推荐初学者范围内的节点，不会引入超纲内容。'
)


def _match_nodes(text: str) -> list[str]:
    lowered = text.lower()
    nodes: list[str] = []
    for keyword, mapped in KEYWORD_TO_NODES.items():
        if keyword in lowered:
            nodes.extend(mapped)
    return list(dict.fromkeys(nodes))


def execute(payload: dict) -> dict:
    weak_points = payload.get('weakPoints') or payload.get('weak_points') or []
    current = payload.get('currentKnowledgePoints') or payload.get('knowledge_points') or []
    error_type = payload.get('errorType') or payload.get('error_type') or 'unknown'
    code_analysis = payload.get('codeAnalysis') or {}
    related_kp = payload.get('relatedKnowledgePoints') or []

    # 1) 优先用诊断给出的关联知识点（带掌握度）
    mastery_by_node: dict[str, str] = {}
    seeded: list[str] = []
    for item in related_kp:
        if isinstance(item, dict) and item.get('node'):
            seeded.append(item['node'])
            mastery_by_node[item['node']] = item.get('mastery', 'unknown')

    related = [n for n in dict.fromkeys(seeded) if n in PYTHON_BEGINNER_NODES]

    # 2) 不足则用关键词匹配补充
    if len(related) < 2:
        seed_text = ' '.join([
            *weak_points, *current, error_type,
            ' '.join(code_analysis.get('relatedConcepts', [])),
        ])
        for node in _match_nodes(seed_text):
            if node in PYTHON_BEGINNER_NODES and node not in related:
                related.append(node)

    if not related:
        related = [n for n in current if n in PYTHON_BEGINNER_NODES][:3] or ['for 循环', 'range', '变量']

    related = related[:5]

    prereq: list[str] = []
    for node in related:
        prereq.extend(PREREQUISITE_MAP.get(node, []))
    prereq = list(dict.fromkeys(prereq))[:4]

    # 复习节点优先放“偏弱 / 未掌握”的关联节点
    weak_first = [n for n in related if mastery_by_node.get(n) in ('weak', 'learning', 'unlearned')]
    review = list(dict.fromkeys([*weak_first, *weak_points[:2], related[0]]))[:3]

    # graphReason 结合真实掌握度，给出更可信的解释
    focus = '、'.join(related[:2]) if related else 'range'
    mastered_focus = [n for n in related if mastery_by_node.get(n) == 'mastered']
    if mastered_focus:
        graph_reason = (
            f'「{"、".join(mastered_focus[:2])}」此前已掌握，本次问题更可能出在细节或迁移上，'
            f'建议结合「{focus}」做针对性巩固。'
        )
    else:
        graph_reason = f'该错误与「{focus}」的理解直接相关，建议先巩固前置知识再练同类题。'

    return {
        'relatedNodes': related,
        'prerequisiteNodes': prereq,
        'recommendedReviewNodes': review,
        'graphReason': graph_reason,
        'masteryByNode': mastery_by_node,
    }
