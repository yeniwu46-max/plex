# -*- coding: utf-8 -*-
"""反馈生成智能体 FeedbackAgent。

根据诊断的 remediationStrategy（补救策略）生成差异化的分层反馈：
不同策略类型给出不同的 stepHints 与 microExercise，让“怎么改”更具体。
"""

ROLE = 'Python 初学者学习反馈教练'
GOAL = '将诊断与策略转化为温和、具体、分层的可读反馈与微型行动'
BACKSTORY = (
    '你从不直接给出完整代码答案，而是按补救策略用 2-3 步提示引导学生自己修正，'
    '并在最后给出明确的下一步行动。'
)

_STRATEGY_ENCOURAGE = {
    'syntax_checklist': '语法细节是熟练度问题，按清单核对几次就会形成肌肉记忆。',
    'concept_explain': '把规则讲清楚后你就会发现，这类题其实有固定套路。',
    'trace_variables': '能把变量变化一步步写出来，说明你已经在像程序一样思考了。',
    'pattern_compare': '你已经掌握了基础题型，迁移只差最后一步，很快就能打通。',
    'micro_fix': '只差一两处小修改，你离正确答案非常近了。',
    'consolidate': '答对了！趁热打铁做一道变式，理解会更牢固。',
}


def execute(payload: dict) -> dict:
    diagnosis = payload.get('diagnosis') or {}
    if isinstance(diagnosis, dict) and 'diagnosis' in diagnosis:
        diagnosis_text = diagnosis.get('diagnosis', '')
        weak = diagnosis.get('weakPoints') or []
    else:
        diagnosis_text = str(diagnosis)
        weak = payload.get('weakPoints') or []

    strategy = diagnosis.get('remediationStrategy') if isinstance(diagnosis, dict) else None
    strategy = strategy if isinstance(strategy, dict) else {}
    strategy_type = strategy.get('type', 'micro_fix')

    code_analysis = payload.get('codeAnalysis') or {}
    recommendation = payload.get('recommendation') or {}

    fix_direction = code_analysis.get('fixDirection', '对照样例逐步检查代码逻辑。')
    next_point = recommendation.get('nextKnowledgePoint', '循环边界')
    exercises = recommendation.get('recommendedExercises') or ['1 到 n 求和']
    focus = weak[0] if weak else next_point

    short_feedback = diagnosis_text or f'你已经接近正确答案，现在需要重点检查{focus}。'

    # 优先采用策略给出的分步提示，并融入代码分析的修改方向
    strategy_steps = strategy.get('steps') or []
    step_hints = []
    if strategy_steps:
        step_hints.append(fix_direction)
        step_hints.extend(strategy_steps)
    else:
        step_hints = [
            fix_direction,
            f'先写出与「{next_point}」相关的小例子，手动推演 2-3 次。',
            '再对照题目要求，确认输出格式与边界是否完全一致。',
        ]
    step_hints = list(dict.fromkeys([s for s in step_hints if s]))[:3]

    micro_exercise = strategy.get('microExercise', '')

    encouragement = _STRATEGY_ENCOURAGE.get(
        strategy_type,
        '这个错误在初学者中很常见，说明你已经进入真正理解代码的阶段了。',
    )

    if strategy_type == 'consolidate':
        next_action = f'建议尝试一道「{exercises[0]}」的变式来巩固{next_point}。'
    else:
        next_action = micro_exercise or f'建议先完成「{exercises[0]}」练习来巩固{next_point}。'

    return {
        'shortFeedback': short_feedback,
        'stepHints': step_hints,
        'encouragement': encouragement,
        'nextAction': next_action,
        'microExercise': micro_exercise,
        'strategyType': strategy_type,
    }
