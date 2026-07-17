# -*- coding: utf-8 -*-
"""教师助理智能体 TeacherAssistantAgent"""

ROLE = 'Python 班级教学助理'
GOAL = '根据班级共性薄弱点生成教学建议与分组干预方案'
BACKSTORY = (
    '你协助教师做班级层面的学情分析，建议表述为「建议」而非绝对结论，'
    '聚焦 Python 初学者常见误区。'
)


def _student_label(student: dict) -> str:
    return str(
        student.get('name')
        or student.get('real_name')
        or student.get('username')
        or student.get('id')
        or '未命名学生'
    )


def _student_weak_labels(student: dict) -> list[str]:
    raw = student.get('weakPoints') or student.get('weak_points') or []
    labels: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            label = item.get('knowledgePoint') or item.get('knowledge_label') or item.get('label')
        else:
            label = item
        if label:
            labels.append(str(label))
    return labels


def _build_real_groups(class_students: list[dict], top_labels: list[str]) -> list[dict]:
    """按学生的薄弱知识点把班级真实学生分到对应干预组。"""
    groups: list[dict] = []
    assigned: set = set()

    for label in top_labels[:3]:
        members = []
        for student in class_students:
            sid = student.get('id')
            if sid in assigned:
                continue
            if label in _student_weak_labels(student):
                members.append(_student_label(student))
                assigned.add(sid)
        if members:
            groups.append({
                'groupName': f'{label} 巩固组',
                'students': members[:12],
                'studentCount': len(members),
                'focus': f'强化「{label}」的理解与练习，配合分层提示卡，避免直接公布答案。',
            })

    # 高频错题但未归入上面分组的活跃学生，归为重点关注组
    high_risk = [
        _student_label(student)
        for student in class_students
        if student.get('id') not in assigned
        and int(student.get('activeCount') or student.get('active_count') or 0) >= 2
    ]
    if high_risk:
        groups.append({
            'groupName': '重点关注组',
            'students': high_risk[:12],
            'studentCount': len(high_risk),
            'focus': '错题积压较多，建议一对一面批，先排查是「不会」还是「会但写错」。',
        })

    return groups


def execute(payload: dict) -> dict:
    weak_stats = payload.get('weakPointStats') or payload.get('weak_point_stats') or []
    common_errors = payload.get('commonErrorTypes') or payload.get('common_error_types') or []
    recent_exercises = payload.get('recentExercises') or payload.get('recent_exercises') or []
    class_students = payload.get('classStudents') or payload.get('class_students') or []

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

    # 优先用真实班级学生构建分组；无学生名单时回退到通用占位分组。
    intervention_groups = _build_real_groups(class_students, top_labels)
    if not intervention_groups:
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
