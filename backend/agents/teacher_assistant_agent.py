# -*- coding: utf-8 -*-
"""教师助理智能体 TeacherAssistantAgent"""

ROLE = 'Python 班级教学助理'
GOAL = '根据班级共性薄弱点生成教学建议与分组干预方案'
BACKSTORY = (
    '你协助教师做班级层面的学情分析，建议表述为「建议」而非绝对结论，'
    '聚焦 Python 初学者常见误区。'
)


def execute(payload: dict) -> dict:
    weak_stats = payload.get('weakPointStats') or payload.get('weak_point_stats') or []
    common_errors = payload.get('commonErrorTypes') or payload.get('common_error_types') or []
    recent_exercises = payload.get('recentExercises') or payload.get('recent_exercises') or []

    if not weak_stats:
        weak_stats = [
            {'knowledgePoint': 'for 循环', 'count': 8},
            {'knowledgePoint': 'range 边界', 'count': 6},
            {'knowledgePoint': '列表下标', 'count': 4},
        ]

    top = sorted(weak_stats, key=lambda x: x.get('count', 0), reverse=True)
    top_labels = [w.get('knowledgePoint', w.get('knowledge_point', '')) for w in top[:3]]
    top_labels = [l for l in top_labels if l]

    error_hint = common_errors[0] if common_errors else 'logic'
    exercise_hint = recent_exercises[0] if recent_exercises else '循环求和练习'

    class_summary = (
        f'本班近期在「{"、".join(top_labels[:2]) or "循环结构"}」上出现较多错误'
        f'（常见类型：{error_hint}），与最近练习「{exercise_hint}」关联度较高。'
    )

    teaching_suggestions = [
        f'建议下节课用可视化方式演示 {top_labels[0] if top_labels else "range"} 的边界规则。',
        '布置 2 道「手动列出循环变量」的小练习，再过渡到编程题。',
        '对反复出错的学生提供分层提示卡，避免直接公布完整代码。',
    ]

    intervention_groups = [
        {
            'groupName': '循环边界待巩固组',
            'students': ['待对接学生名单'],
            'focus': f'强化 {top_labels[0] if top_labels else "range 边界"} 与 off-by-one 意识',
        },
        {
            'groupName': '语法基础复查组',
            'students': ['待对接学生名单'],
            'focus': '复查缩进、冒号与变量命名等基础语法',
        },
    ]

    return {
        'classSummary': class_summary,
        'teachingSuggestions': teaching_suggestions,
        'interventionGroups': intervention_groups,
    }
