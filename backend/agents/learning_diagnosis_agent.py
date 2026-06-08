# -*- coding: utf-8 -*-
"""学习诊断智能体 LearningDiagnosisAgent"""

ROLE = 'Python 初学者学习诊断专家'
GOAL = '识别学生当前薄弱知识点与错误类型，给出可解释的诊断结论'
BACKSTORY = (
    '你长期辅导 Python 零基础学生，擅长从答题记录与运行结果中判断'
    '是语法、逻辑还是概念理解问题，从不说打击性语言。'
)

ERROR_TYPE_HINTS = {
    'IndexError': ('logic', '列表或循环边界'),
    'TypeError': ('concept', '数据类型与运算'),
    'NameError': ('syntax', '变量命名与定义'),
    'SyntaxError': ('syntax', 'Python 语法'),
    'IndentationError': ('syntax', '缩进与代码块'),
    'ValueError': ('input_output', '输入输出与类型转换'),
    'ZeroDivisionError': ('logic', '除零与条件判断'),
}


def execute(payload: dict) -> dict:
    knowledge_points = payload.get('knowledgePoints') or payload.get('knowledge_points') or []
    attempt_count = int(payload.get('attemptCount') or payload.get('attempt_count') or 1)
    answer_status = payload.get('answerStatus') or payload.get('answer_status') or 'wrong'
    error_message = payload.get('errorMessage') or payload.get('error_message') or payload.get('stderr') or ''
    recent_mistakes = payload.get('recentMistakes') or payload.get('recent_mistakes') or []

    error_type = 'unknown'
    weak_points: list[str] = []

    for exc, (etype, label) in ERROR_TYPE_HINTS.items():
        if exc.lower() in (error_message + str(payload.get('code', ''))).lower():
            error_type = etype
            weak_points.append(label)
            break

    if 'range' in error_message.lower() or 'range' in str(payload.get('code', '')).lower():
        weak_points.extend(['range 边界', 'for 循环'])
        if error_type == 'unknown':
            error_type = 'logic'

    if not weak_points:
        weak_points = list(knowledge_points[:2]) or list(recent_mistakes[:2]) or ['循环边界', 'for 循环']

    weak_points = list(dict.fromkeys(weak_points))[:3]

    if answer_status == 'correct':
        diagnosis = '本次作答正确，建议巩固同类题型并尝试稍难一点的变式。'
        confidence = 0.92
        error_type = 'unknown'
    elif attempt_count >= 3:
        diagnosis = (
            f'学生可能已经理解{weak_points[0]}的大致思路，'
            f'但在{weak_points[-1]}细节上还不稳定，需要分层提示而非直接给答案。'
        )
        confidence = 0.84
    else:
        diagnosis = (
            f'学生可能理解了相关结构，但对{"、".join(weak_points)}的理解还不够稳定，'
            '建议结合小例子手动推演。'
        )
        confidence = 0.86

    return {
        'weakPoints': weak_points,
        'errorType': error_type,
        'diagnosis': diagnosis,
        'confidence': round(confidence, 2),
    }
