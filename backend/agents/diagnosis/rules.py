# -*- coding: utf-8 -*-
"""四层错因规则库。

从原 ``learning_diagnosis_agent.ERROR_TYPE_HINTS`` 与
``code_analysis_agent.ANALYSIS_RULES`` 迁移并扩展为带优先级的规则表。
每条规则给出：错因层级、子类、关联知识点、置信度、补救策略与代码层面的解释，
按 ``priority`` 从高到低匹配，命中首条即返回。

匹配函数签名统一为 ``match(ctx, signals) -> bool``：
- ``ctx``  : DiagnosisContext
- ``signals`` : analyzer 产出的轻量静态分析结果（dict）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .schema import DiagnosisContext

MatchFn = Callable[[DiagnosisContext, dict], bool]


@dataclass
class Rule:
    layer: str
    subtype: str
    match: MatchFn
    knowledge: list[str]
    confidence: float
    strategy: str
    summary: str  # 面向学生的一句话问题概述
    cause: str    # 可能原因
    fix: str      # 修改方向（不直接给答案）
    priority: int = 50
    evidence_tag: str = ''

    def __post_init__(self) -> None:
        if not self.evidence_tag:
            self.evidence_tag = f'{self.layer}:{self.subtype}'


def _stderr_has(ctx: DiagnosisContext, *needles: str) -> bool:
    blob = (ctx.stderr + '\n' + ctx.error_message).lower()
    return any(n.lower() in blob for n in needles)


# ============================ 规则表 ============================
# priority: 90+ 语法/运行期硬证据；70-89 规则层；50-69 逻辑层；30-49 迁移层；
# 兜底规则在 engine 中单独处理。

RULES: list[Rule] = [
    # ---------------- 语法层 ----------------
    Rule(
        layer='syntax', subtype='missing_colon', priority=96,
        match=lambda ctx, s: s.get('syntax_error') and s.get('syntax_hint') == 'missing_colon',
        knowledge=['if 条件分支', 'for 循环', 'while 循环'],
        confidence=0.95, strategy='syntax_checklist',
        summary='代码块起始行缺少冒号。',
        cause='if / for / while / def 等语句末尾需要英文冒号 `:`，漏写会触发 SyntaxError。',
        fix='检查每个 if/for/while/def 行尾是否都有英文冒号。',
    ),
    Rule(
        layer='syntax', subtype='indentation', priority=95,
        match=lambda ctx, s: _stderr_has(ctx, 'indentationerror', 'taberror')
        or s.get('syntax_hint') == 'indentation',
        knowledge=['if 条件分支', 'for 循环'],
        confidence=0.94, strategy='syntax_checklist',
        summary='缩进不正确，Python 代码块层级混乱。',
        cause='代码块（if/for 内部）需要统一缩进，常见混用 Tab 与空格，或少缩进 4 个空格。',
        fix='确保同一代码块缩进一致，建议统一用 4 个空格。',
    ),
    Rule(
        layer='syntax', subtype='name_typo', priority=92,
        match=lambda ctx, s: _stderr_has(ctx, 'nameerror') and s.get('name_typo'),
        knowledge=['变量'],
        confidence=0.9, strategy='syntax_checklist',
        summary='变量名拼写与定义处不一致。',
        cause='使用的变量名和定义时拼写不同（大小写或字母差异），Python 视为未定义变量。',
        fix='核对报错变量名与你定义处的拼写是否完全一致。',
    ),
    Rule(
        layer='syntax', subtype='name_undefined', priority=88,
        match=lambda ctx, s: _stderr_has(ctx, 'nameerror'),
        knowledge=['变量', '输入 input'],
        confidence=0.86, strategy='concept_explain',
        summary='使用了尚未定义（赋值）的变量。',
        cause='变量在使用前没有先赋值，或赋值语句写在了使用之后。',
        fix='确认变量在第一次使用之前已经完成赋值。',
    ),
    Rule(
        layer='syntax', subtype='syntax_generic', priority=85,
        match=lambda ctx, s: _stderr_has(ctx, 'syntaxerror') or s.get('syntax_error'),
        knowledge=['变量', 'print 输出'],
        confidence=0.84, strategy='syntax_checklist',
        summary='Python 语法不符合规范。',
        cause='可能缺少冒号、括号 / 引号不匹配，或语句结构不完整。',
        fix='逐行检查括号、引号是否成对，冒号是否遗漏。',
    ),

    # ---------------- 规则层 ----------------
    Rule(
        layer='rule', subtype='range_exclusive_end', priority=82,
        match=lambda ctx, s: s.get('uses_range') and (ctx.output_mismatch or s.get('off_by_one')),
        knowledge=['range', 'for 循环', '循环边界'],
        confidence=0.88, strategy='concept_explain',
        summary='循环次数比预期少一次（或边界不符）。',
        cause='range(a, b) 是左闭右开，不包含 b，常见 off-by-one 错误。',
        fix='想清楚需要循环到哪个数，必要时把 range 的结束值 +1。',
    ),
    Rule(
        layer='rule', subtype='index_out_of_range', priority=80,
        match=lambda ctx, s: _stderr_has(ctx, 'indexerror'),
        knowledge=['列表', 'for 循环', '循环边界'],
        confidence=0.87, strategy='trace_variables',
        summary='访问了列表中不存在的下标。',
        cause='下标从 0 开始到 len-1，循环用了 len 或 len+1 作为上界就会越界。',
        fix='确认循环变量范围是 0 到 len-1，或直接遍历元素而非下标。',
    ),
    Rule(
        layer='rule', subtype='type_conversion', priority=78,
        match=lambda ctx, s: _stderr_has(ctx, 'typeerror', 'valueerror')
        and (s.get('uses_input') or 'int(' not in ctx.code),
        knowledge=['类型转换', '输入 input', '算术运算'],
        confidence=0.85, strategy='concept_explain',
        summary='对不兼容的类型做了运算或转换。',
        cause='input() 读入的是字符串，直接与数字运算或未做 int()/float() 转换。',
        fix='先用 int() 或 float() 把输入转换为数字再参与计算。',
    ),
    Rule(
        layer='rule', subtype='zero_division', priority=76,
        match=lambda ctx, s: _stderr_has(ctx, 'zerodivisionerror'),
        knowledge=['算术运算', 'if 条件分支'],
        confidence=0.86, strategy='concept_explain',
        summary='发生了除以 0 的运算。',
        cause='除数在某些情况下取到了 0，没有提前判断。',
        fix='在做除法前先判断除数是否为 0。',
    ),

    # ---------------- 逻辑层 ----------------
    Rule(
        layer='logic', subtype='while_termination', priority=66,
        match=lambda ctx, s: s.get('while_no_update') or s.get('infinite_loop_risk'),
        knowledge=['while 循环', '循环边界', '比较运算'],
        confidence=0.9, strategy='trace_variables',
        summary='while 循环条件可能永远成立，形成死循环。',
        cause='循环体内没有更新条件变量，循环条件一直为 True。',
        fix='确认循环体内有改变条件变量的语句，让循环最终能停止。',
    ),
    Rule(
        layer='logic', subtype='accumulator_not_init', priority=62,
        match=lambda ctx, s: s.get('accumulator_use_before_init'),
        knowledge=['累加求和', '变量', 'for 循环'],
        confidence=0.82, strategy='trace_variables',
        summary='累加 / 计数变量在循环前没有初始化。',
        cause='求和、计数需要在循环外先把变量设为 0，否则结果错误或报错。',
        fix='在循环开始前把累加 / 计数变量初始化为 0。',
    ),
    Rule(
        layer='logic', subtype='condition_reversed', priority=58,
        match=lambda ctx, s: s.get('condition_suspect') and ctx.output_mismatch,
        knowledge=['if 条件分支', '比较运算', '逻辑运算'],
        confidence=0.78, strategy='trace_variables',
        summary='判断条件方向可能写反了。',
        cause='比较运算符（> 与 <、>= 与 <=）方向写反，导致分支走错。',
        fix='代入一个具体例子，验证条件为真 / 为假时是否符合题意。',
    ),
    Rule(
        layer='logic', subtype='loop_logic_generic', priority=54,
        match=lambda ctx, s: s.get('has_loop') and ctx.output_mismatch and not s.get('transfer_gap'),
        knowledge=['for 循环', 'range', '循环边界'],
        confidence=0.74, strategy='trace_variables',
        summary='循环逻辑未覆盖全部情况，结果与预期不符。',
        cause='循环范围、累加位置或更新时机与题目要求不一致。',
        fix='手动写出前 2-3 次循环的变量值，对照预期定位偏差。',
    ),

    # ---------------- 迁移层 ----------------
    Rule(
        layer='transfer', subtype='pattern_transfer_gap', priority=44,
        match=lambda ctx, s: s.get('transfer_gap'),
        knowledge=['最大值最小值', '线性查找', '累加求和'],
        confidence=0.8, strategy='pattern_compare',
        summary='相似题型已掌握，但本题的变式迁移没有完成。',
        cause='你会写基础遍历（如求和），但换成求最大值 / 查找时遍历结构没迁移过来。',
        fix='回想已会题型的遍历骨架，只替换“每一步要做的事”。',
    ),
    Rule(
        layer='transfer', subtype='template_copy', priority=40,
        match=lambda ctx, s: s.get('template_copy_suspect'),
        knowledge=['for 循环', '变量'],
        confidence=0.72, strategy='pattern_compare',
        summary='代码像是照抄模板，但关键参数 / 条件没有按本题改。',
        cause='套用了示例代码框架，却没有把变量名、范围或判断条件改成本题需要的。',
        fix='逐行确认模板里的每个变量和条件是否都换成了本题的数据。',
    ),
]

RULES.sort(key=lambda r: -r.priority)
