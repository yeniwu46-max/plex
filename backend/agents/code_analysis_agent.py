# -*- coding: utf-8 -*-
"""代码分析智能体 CodeAnalysisAgent"""

ROLE = 'Python 初学者代码分析助教'
GOAL = '解释学生代码中的错误原因，给出修改方向，不直接给出完整答案'
BACKSTORY = (
    '你擅长把编译器与运行时的报错翻译成初学者能懂的语言，'
    '总是温和地指出问题并引导他们自己修正。'
)

ANALYSIS_RULES = [
    (
        lambda p: 'range' in p.get('code', '').lower() and any(
            w in (p.get('stderr') or '').lower() for w in ('少', 'wrong', 'fail', 'index')
        ),
        {
            'codeIssueSummary': '循环少执行了一次或边界不符合题目要求。',
            'possibleCause': 'range 的结束值不包含在循环范围内，常见 off-by-one 错误。',
            'fixDirection': '检查 range 的第二个参数是否需要加 1，或手动列出循环变量变化。',
            'relatedConcepts': ['for 循环', 'range', '循环边界'],
        },
    ),
    (
        lambda p: 'indexerror' in (p.get('stderr') or '').lower(),
        {
            'codeIssueSummary': '访问了列表中不存在的下标。',
            'possibleCause': '循环次数与列表长度不一致，或使用了 len+1 作为上界。',
            'fixDirection': '检查循环变量是否从 0 到 len-1，或改用直接遍历元素。',
            'relatedConcepts': ['列表', 'for 循环', '循环边界'],
        },
    ),
    (
        lambda p: 'syntaxerror' in (p.get('stderr') or '').lower() or 'indentationerror' in (p.get('stderr') or '').lower(),
        {
            'codeIssueSummary': 'Python 语法或缩进不符合要求。',
            'possibleCause': '可能缺少冒号、括号不匹配，或 if/for 代码块缩进不正确。',
            'fixDirection': '逐行检查冒号与缩进，确保代码块比上一行多 4 个空格。',
            'relatedConcepts': ['if 条件分支', 'for 循环', '变量'],
        },
    ),
    (
        lambda p: 'nameerror' in (p.get('stderr') or '').lower(),
        {
            'codeIssueSummary': '使用了尚未定义的变量名。',
            'possibleCause': '变量拼写错误或在使用前未赋值。',
            'fixDirection': '确认变量名拼写，并在使用前完成赋值。',
            'relatedConcepts': ['变量', '输入 input'],
        },
    ),
    (
        lambda p: 'typeerror' in (p.get('stderr') or '').lower(),
        {
            'codeIssueSummary': '对不兼容的类型进行了运算或比较。',
            'possibleCause': 'input 读入的是字符串，却直接与数字运算。',
            'fixDirection': '使用 int() 或 float() 做类型转换后再计算。',
            'relatedConcepts': ['类型转换', '输入 input', '算术运算'],
        },
    ),
]


def execute(payload: dict) -> dict:
    for matcher, result in ANALYSIS_RULES:
        if matcher(payload):
            return dict(result)

    stderr = payload.get('stderr') or payload.get('errorMessage') or ''
    code = payload.get('code', '')
    if stderr.strip():
        return {
            'codeIssueSummary': '程序运行未通过，输出或逻辑与预期不一致。',
            'possibleCause': stderr.strip()[:120],
            'fixDirection': '对照预期输出，用 print 打印中间变量，逐步缩小问题范围。',
            'relatedConcepts': ['变量', 'print 输出'],
        }

    if 'for' in code or 'while' in code:
        return {
            'codeIssueSummary': '循环逻辑可能未覆盖全部情况。',
            'possibleCause': '循环条件或 range 边界与题目要求不一致。',
            'fixDirection': '手动写出前三次循环的变量值，确认是否遗漏最后一次。',
            'relatedConcepts': ['for 循环', 'range'],
        }

    return {
        'codeIssueSummary': '代码结构基本可读，但结果仍未满足题目要求。',
        'possibleCause': '可能是边界条件或输出格式与样例不一致。',
        'fixDirection': '逐条对照样例输入输出，检查是否多输出了空格或换行。',
        'relatedConcepts': ['print 输出', '变量'],
    }
