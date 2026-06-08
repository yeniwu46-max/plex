# -*- coding: utf-8 -*-
"""知识图谱智能体 KnowledgeGraphAgent"""

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

    seed_text = ' '.join([*weak_points, *current, error_type, ' '.join(code_analysis.get('relatedConcepts', []))])
    related = _match_nodes(seed_text)
    if not related:
        related = [n for n in current if n in PYTHON_BEGINNER_NODES][:3]
    if not related:
        related = ['for 循环', 'range', '变量']

    related = [n for n in dict.fromkeys(related) if n in PYTHON_BEGINNER_NODES][:5]

    prereq: list[str] = []
    for node in related:
        prereq.extend(PREREQUISITE_MAP.get(node, []))
    prereq = list(dict.fromkeys(prereq))[:4]

    review = list(dict.fromkeys([*weak_points[:2], related[0] if related else 'range']))[:3]

    return {
        'relatedNodes': related,
        'prerequisiteNodes': prereq,
        'recommendedReviewNodes': review,
        'graphReason': '该错误与「{}」的理解直接相关，建议先巩固前置知识再练同类题。'.format(
            '、'.join(related[:2]),
        ),
    }
