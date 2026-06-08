# -*- coding: utf-8 -*-
"""路径推荐智能体 PathRecommendationAgent"""

from .knowledge_scope import EXERCISE_BY_TOPIC

ROLE = 'Python 学习路径规划师'
GOAL = '根据诊断与图谱结果推荐下一步知识点与 1-3 道练习'
BACKSTORY = (
    '你坚持先补前置、不跳级、每次只推少量练习，'
    '帮助初学者稳步建立 Python 基础。'
)


def execute(payload: dict) -> dict:
    weak_points = payload.get('weakPoints') or payload.get('weak_points') or []
    prereq_nodes = payload.get('prerequisiteNodes') or payload.get('prerequisite_nodes') or []
    graph_insight = payload.get('graphInsight') or {}

    focus = weak_points[0] if weak_points else 'for 循环'
    if graph_insight.get('recommendedReviewNodes'):
        focus = graph_insight['recommendedReviewNodes'][0]

    exercises = EXERCISE_BY_TOPIC.get(focus, EXERCISE_BY_TOPIC['default'])[:2]
    if len(exercises) < 2:
        exercises = list(dict.fromkeys([*exercises, *EXERCISE_BY_TOPIC['default']]))[:2]

    review_plan = [
        f'复习 {prereq_nodes[0]}' if prereq_nodes else '复习变量与基本类型',
        f'手动推演 {focus} 的小例子',
        f'完成 {exercises[0]} 巩固练习',
    ]

    difficulty = 'easy' if len(weak_points) <= 1 else 'medium'

    return {
        'nextKnowledgePoint': focus if focus in EXERCISE_BY_TOPIC or focus else 'range 的边界规则',
        'recommendedExercises': exercises[:3],
        'reviewPlan': review_plan[:3],
        'estimatedDifficulty': difficulty,
    }
