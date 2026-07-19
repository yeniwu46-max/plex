# -*- coding: utf-8 -*-
"""试炼编程页 · 三类辅导智能体 + 自由问答（均禁止直接给出答案）。"""

from __future__ import annotations

import json
from typing import Any

from agents.llm_client import api_key_configured, chat_json, chat_text, llm_provider, strip_asterisks

INTENT_ERROR = 'error_diagnosis'
INTENT_QUALITY = 'code_quality'
INTENT_OPTIMIZE = 'optimization'
INTENT_CUSTOM = 'custom'

VALID_INTENTS = {INTENT_ERROR, INTENT_QUALITY, INTENT_OPTIMIZE, INTENT_CUSTOM}

AGENT_META: dict[str, dict[str, str]] = {
    INTENT_ERROR: {
        'id': 'trial_error_diagnosis',
        'name': '报错分析智能体',
        'role': 'Python 报错引导教练',
    },
    INTENT_QUALITY: {
        'id': 'trial_code_quality',
        'name': '代码质量分析智能体',
        'role': 'Python 代码质量评审教练',
    },
    INTENT_OPTIMIZE: {
        'id': 'trial_optimization',
        'name': '优化建议智能体',
        'role': 'Python 代码优化引导教练',
    },
    INTENT_CUSTOM: {
        'id': 'trial_custom_coach',
        'name': '编程辅导智能体',
        'role': 'Python 编程辅导教练',
    },
}

NO_ANSWER_POLICY = 'no_direct_answer'

NO_ANSWER_RULE = (
    '【硬性规则】你是耐心的 Python 编程辅导老师。'
    '绝对不能给出完整答案、不能直接给出可通过测试的代码、不能写出预期输出的完整解法。'
    '只能用提问、思路引导、检查清单和类比，帮助学生自己发现和修正。'
    '回复使用简洁中文，150字以内优先；必要时可稍长，但仍不得泄露答案。'
    '不要使用星号（*）或 Markdown 加粗。'
)


def _answer_status(payload: dict) -> str:
    explicit = str(payload.get('answerStatus') or '').strip()
    if explicit in {'correct', 'wrong', 'partial', 'not_run'}:
        return explicit
    all_passed = payload.get('allPassed')
    case_results = payload.get('caseResults') or []
    if not case_results:
        return 'not_run'
    if all_passed is True:
        return 'correct'
    passed = sum(1 for item in case_results if item.get('passed'))
    if passed and passed < len(case_results):
        return 'partial'
    return 'wrong'


def _build_context_summary(payload: dict) -> str:
    title = str(payload.get('questionTitle') or payload.get('exerciseId') or '当前题目')
    topic = str(payload.get('topic') or '')
    status = _answer_status(payload)
    status_label = {
        'correct': '全部通过',
        'wrong': '未通过',
        'partial': '部分通过',
        'not_run': '尚未运行测试',
    }.get(status, status)
    parts = [f'题目「{title}」']
    if topic:
        parts.append(f'知识点：{topic}')
    parts.append(f'当前状态：{status_label}')
    code = str(payload.get('code') or '').strip()
    if code:
        parts.append(f'已编写 {len(code.splitlines())} 行代码')
    else:
        parts.append('代码区为空')
    return ' · '.join(parts)


def _build_context_block(payload: dict) -> str:
    status = _answer_status(payload)
    parts = [
        f'题目：{payload.get("questionTitle") or payload.get("exerciseId")}',
        f'题面：{payload.get("questionPrompt") or payload.get("description") or "（无）"}',
        f'知识点：{payload.get("topic") or "（无）"}',
        f'运行状态：{status}',
        f'学生代码：\n{payload.get("code") or "（空）"}',
    ]
    if payload.get('stderr'):
        parts.append(f'报错信息：{payload.get("stderr")}')
    if payload.get('stdout'):
        parts.append(f'实际输出：{payload.get("stdout")}')
    if payload.get('expectedOutput'):
        parts.append(f'预期输出：{payload.get("expectedOutput")}')
    failed = payload.get('failedCases') or []
    if failed:
        parts.append(f'未通过用例：{json.dumps(failed, ensure_ascii=False)}')
    return '\n'.join(parts)


def _intent_focus(intent: str) -> str:
    if intent == INTENT_ERROR:
        return '重点帮助学生理解「为什么出错」，用 2-3 个引导性问题收尾。'
    if intent == INTENT_QUALITY:
        return '重点评价代码可读性、结构与规范，指出 2-3 条可改进方向，可顺带肯定 1 条优点。'
    if intent == INTENT_OPTIMIZE:
        return '重点提出效率或结构优化思路，以反思问题收尾，不给可直接提交的代码。'
    return '根据学生问题，结合题目与代码上下文给出启发式辅导。'


def _llm_prompt(intent: str) -> str:
    base = NO_ANSWER_RULE
    if intent == INTENT_ERROR:
        return (
            f'{base} {_intent_focus(intent)}'
            '输出 JSON：response(字符串,120字内)、'
            'guidingQuestions(字符串数组,2-3个)、checklist(字符串数组,2-3条)。只输出 JSON。'
        )
    if intent == INTENT_QUALITY:
        return (
            f'{base} {_intent_focus(intent)}'
            '输出 JSON：response(字符串,120字内)、'
            'strengths(字符串数组,1-2条)、improvements(字符串数组,2-3条,不含具体代码)。只输出 JSON。'
        )
    if intent == INTENT_OPTIMIZE:
        return (
            f'{base} {_intent_focus(intent)}'
            '输出 JSON：response(字符串,120字内)、'
            'suggestions(字符串数组,2-3条)、reflectionQuestions(字符串数组,1-2个)。只输出 JSON。'
        )
    return f'{base} {_intent_focus(intent)}'


def _chat_system(intent: str) -> str:
    return f'{NO_ANSWER_RULE}\n{_intent_focus(intent)}'


def _rules_error(payload: dict) -> dict[str, Any]:
    stderr = str(payload.get('stderr') or '').strip()
    failed = payload.get('failedCases') or []
    status = _answer_status(payload)

    if status == 'not_run':
        return {
            'response': '你还没有运行测试。先写一版思路代码，点击「运行测试」，我才能根据报错或输出差异帮你分析。',
            'guidingQuestions': [
                '题目要求你输出什么？你的代码里哪一步负责产生这个结果？',
                '如果手动模拟输入，你期望程序走哪几步？',
            ],
            'checklist': ['确认是否使用了题目要求的语法点', '检查输出格式是否与样例一致'],
        }

    if status == 'correct':
        return {
            'response': '当前测试已全部通过。若仍想排查潜在问题，可以回顾边界情况是否都覆盖到了。',
            'guidingQuestions': [
                '如果输入换成样例里没有的数值，你的代码还能正确吗？',
                '有没有哪一行是「碰巧通过」但逻辑不够清晰的？',
            ],
            'checklist': ['尝试 mentally 走一遍循环/分支', '确认没有硬编码样例输出'],
        }

    if stderr:
        lower = stderr.lower()
        if 'syntaxerror' in lower or 'indentationerror' in lower:
            hint = '看起来是语法或缩进问题，先定位报错行号附近。'
        elif 'nameerror' in lower:
            hint = '可能有变量名拼写或未定义就使用的情况。'
        elif 'typeerror' in lower:
            hint = '可能在类型不匹配的地方做了运算或调用。'
        elif 'indexerror' in lower:
            hint = '列表或字符串下标可能越界了，检查循环边界。'
        else:
            hint = '运行时报错，请从报错信息提到的行开始往上追溯。'
        return {
            'response': hint,
            'guidingQuestions': [
                '报错信息里提到的变量/行，在你的代码里实际是什么？',
                '如果把那一行单独拿出来，输入是否和题目假设一致？',
            ],
            'checklist': ['对照报错行检查拼写与缩进', '确认是否使用了题目给定的变量名'],
        }

    first = failed[0] if failed else {}
    label = str(first.get('label') or '某个用例')
    return {
        'response': f'「{label}」未通过，说明输出或逻辑与预期不一致。不要直接改输出，先找出哪一步产生了差异。',
        'guidingQuestions': [
            '预期输出和实际输出，第一个不同的字符出现在哪里？',
            '对于该用例的输入，你手动推算的结果和程序输出一致吗？',
        ],
        'checklist': ['检查是否多/少了空格或换行', '确认循环次数和边界条件'],
    }


def _rules_quality(payload: dict) -> dict[str, Any]:
    code = str(payload.get('code') or '').strip()
    if not code:
        return {
            'response': '代码区还是空的。先写出解题骨架，再讨论质量与规范。',
            'strengths': [],
            'improvements': ['补充核心逻辑后再检查命名与结构', '保持函数/主流程层次清晰'],
        }

    strengths: list[str] = []
    improvements: list[str] = []

    if '\n' in code and len(code.splitlines()) >= 3:
        strengths.append('代码有一定结构，不是单行堆砌。')
    if 'def ' in code:
        strengths.append('使用了函数封装，便于复用与测试。')
    if not strengths:
        strengths.append('已开始编写，可以继续完善逻辑。')

    if code.count('print(') > 3:
        improvements.append('print 较多，思考哪些用于调试、哪些应保留在最终逻辑里。')
    if 'pass' in code:
        improvements.append('存在 pass 占位，确认是否还有未完成的分支或函数体。')
    if len(code.splitlines()) == 1 and len(code) > 60:
        improvements.append('单行过长，可考虑拆成多步以便阅读和排错。')
    if not improvements:
        improvements.append('给关键变量起能表达含义的名字，方便后续修改。')
        improvements.append('在复杂判断或循环旁加简短注释，帮助未来的自己理解。')

    return {
        'response': '从可读性与结构角度，你的代码有可以打磨的空间，但不必追求一次写完美。',
        'strengths': strengths[:2],
        'improvements': improvements[:3],
    }


def _rules_optimize(payload: dict) -> dict[str, Any]:
    code = str(payload.get('code') or '').strip()
    status = _answer_status(payload)

    if not code:
        return {
            'response': '还没有代码可优化。先实现基本功能，再考虑效率和结构改进。',
            'suggestions': ['先保证正确性，再讨论优化', '把重复逻辑提取成函数或循环'],
            'reflectionQuestions': ['题目最小需要哪几步计算？'],
        }

    suggestions: list[str] = []
    if 'for ' in code and 'range(len(' in code:
        suggestions.append('遍历列表时，思考是否可以直接按元素迭代，减少下标出错风险。')
    if code.count('if ') >= 3:
        suggestions.append('多个 if 分支也许可以合并条件或提前 return，让主流程更短。')
    if status == 'correct':
        suggestions.append('已通过测试，可以尝试减少临时变量或合并步骤，看是否更清晰。')
    else:
        suggestions.append('先修正逻辑错误，再优化；过早优化可能掩盖根本问题。')
    if len(suggestions) < 2:
        suggestions.append('检查是否有重复计算可以缓存到变量里。')

    return {
        'response': '优化不等于改答案，而是在正确前提下让代码更清晰或更高效。',
        'suggestions': suggestions[:3],
        'reflectionQuestions': [
            '如果输入规模变大，哪一步会成为瓶颈？',
            '有没有两段逻辑在做类似的事，可以合并？',
        ],
    }


def _rules_custom(payload: dict, user_question: str) -> dict[str, Any]:
    q = user_question.lower()
    if '错' in user_question or '报错' in user_question or 'error' in q:
        body = _rules_error(payload)
    elif '质量' in user_question or '规范' in user_question:
        body = _rules_quality(payload)
    elif '优化' in user_question:
        body = _rules_optimize(payload)
    else:
        body = {
            'response': '我已看到当前题目和你的代码。你可以先描述卡在哪一步，或点击上方快捷问题让我更有针对性地引导。',
            'guidingQuestions': ['你现在最不确定的是语法、逻辑还是输出格式？'],
        }
    return body


def _rules_result(intent: str, payload: dict, user_question: str = '') -> dict[str, Any]:
    if intent == INTENT_ERROR:
        return _rules_error(payload)
    if intent == INTENT_QUALITY:
        return _rules_quality(payload)
    if intent == INTENT_OPTIMIZE:
        return _rules_optimize(payload)
    return _rules_custom(payload, user_question)


def _format_chat_response(body: dict[str, Any]) -> str:
    lines = [str(body.get('response') or '').strip()]
    for key, title in (
        ('guidingQuestions', '你可以思考'),
        ('reflectionQuestions', '反思一下'),
        ('checklist', '自查清单'),
        ('strengths', '优点'),
        ('improvements', '改进方向'),
        ('suggestions', '优化方向'),
    ):
        items = body.get(key)
        if isinstance(items, list) and items:
            lines.append(f'{title}：')
            lines.extend(f'· {item}' for item in items[:4])
    return '\n'.join(line for line in lines if line).strip()


def execute(intent: str, payload: dict) -> dict:
    """运行指定 intent 的试炼辅导智能体。"""
    if intent not in VALID_INTENTS:
        raise ValueError(f'unsupported intent: {intent}')

    meta = AGENT_META[intent]
    context_summary = _build_context_summary(payload)
    user_question = str(payload.get('userQuestion') or payload.get('user_question') or '').strip()
    history = payload.get('conversationHistory') or payload.get('conversation_history') or []
    body: dict[str, Any] = _rules_result(intent, payload, user_question)
    backend = 'rules'

    llm_context = {
        'questionTitle': payload.get('questionTitle'),
        'questionPrompt': payload.get('questionPrompt') or payload.get('description'),
        'topic': payload.get('topic'),
        'code': payload.get('code'),
        'stderr': payload.get('stderr'),
        'stdout': payload.get('stdout'),
        'expectedOutput': payload.get('expectedOutput'),
        'failedCases': payload.get('failedCases'),
        'answerStatus': _answer_status(payload),
        'constraints': payload.get('constraints'),
        'userQuestion': user_question,
    }

    provider = llm_provider()
    if provider and user_question:
        prompt_user = (
            f'【练习上下文】\n{_build_context_block(payload)}\n\n'
            f'【学生问题】\n{user_question}'
        )
        text = chat_text(
            system=_chat_system(intent),
            user=prompt_user,
            history=history if isinstance(history, list) else None,
            timeout=40.0,
            max_tokens=900,
        )
        if text:
            body = {'response': text[:1200]}
            backend = provider[2].split('/')[-1] if 'deepseek' in provider[1] else 'llm'
            if 'deepseek' in provider[1]:
                backend = 'deepseek'
    elif api_key_configured():
        llm_out = chat_json(
            system=_llm_prompt(intent),
            user=json.dumps(llm_context, ensure_ascii=False),
            timeout=35.0,
        )
        if llm_out and llm_out.get('response'):
            body = {**body, **{k: v for k, v in llm_out.items() if v}}
            backend = 'deepseek' if llm_provider() and 'deepseek' in (llm_provider() or ('', '', ''))[1] else 'llm'

    response_text = _format_chat_response(body) if not user_question else str(body.get('response') or '')

    return {
        'agentId': meta['id'],
        'agentName': meta['name'],
        'intent': intent,
        'contextSummary': context_summary,
        'response': strip_asterisks(response_text[:1200]),
        'guidingQuestions': body.get('guidingQuestions') or body.get('reflectionQuestions') or [],
        'strengths': body.get('strengths') or [],
        'improvements': body.get('improvements') or body.get('suggestions') or body.get('checklist') or [],
        'policy': NO_ANSWER_POLICY,
        'backend': backend,
    }
