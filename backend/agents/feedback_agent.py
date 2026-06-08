# -*- coding: utf-8 -*-
"""反馈生成智能体 FeedbackAgent"""

ROLE = 'Python 初学者学习反馈教练'
GOAL = '将诊断与分析转化为温和、具体、分层的可读反馈'
BACKSTORY = (
    '你从不直接给出完整代码答案，而是用 2-3 步提示引导学生自己修正，'
    '并在最后给出明确的下一步行动。'
)


def execute(payload: dict) -> dict:
    diagnosis = payload.get('diagnosis') or {}
    if isinstance(diagnosis, dict) and 'diagnosis' in diagnosis:
        diagnosis_text = diagnosis.get('diagnosis', '')
        weak = diagnosis.get('weakPoints') or []
    else:
        diagnosis_text = str(diagnosis)
        weak = payload.get('weakPoints') or []

    code_analysis = payload.get('codeAnalysis') or {}
    recommendation = payload.get('recommendation') or {}

    fix_direction = code_analysis.get('fixDirection', '对照样例逐步检查代码逻辑。')
    next_point = recommendation.get('nextKnowledgePoint', '循环边界')
    exercises = recommendation.get('recommendedExercises') or ['1 到 n 求和']
    focus = weak[0] if weak else next_point

    short_feedback = diagnosis_text or f'你已经接近正确答案，现在需要重点检查{focus}。'

    step_hints = [
        fix_direction,
        f'先写出与「{next_point}」相关的小例子，手动推演 2-3 次循环。',
        '再对照题目要求，确认输出格式与边界是否完全一致。',
    ][:3]

    encouragement = '这个错误在初学者中很常见，说明你已经进入真正理解代码的阶段了。'
    next_action = f'建议先完成「{exercises[0]}」练习来巩固{next_point}。'

    return {
        'shortFeedback': short_feedback,
        'stepHints': step_hints,
        'encouragement': encouragement,
        'nextAction': next_action,
    }
