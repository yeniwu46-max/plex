# -*- coding: utf-8 -*-
"""轻量静态分析：用标准库 ast 抽取触发规则所需的信号。

不引入任何第三方依赖。所有分析都是“尽力而为”，解析失败时退化为
基于字符串 / stderr 的启发式，绝不抛出异常影响主流程。
"""

from __future__ import annotations

import ast
import re

from .schema import DiagnosisContext

_NAME_ERROR_RE = re.compile(r"name '([^']+)' is not defined", re.IGNORECASE)


def _similar(a: str, b: str) -> float:
    """两个标识符的相似度（基于编辑距离的简单比值）。"""
    a, b = a.lower(), b.lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # Levenshtein 距离
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    dist = prev[-1]
    return 1.0 - dist / max(len(a), len(b))


def _detect_name_typo(ctx: DiagnosisContext, defined_names: set[str]) -> bool:
    """报错的未定义变量是否与某个已定义变量高度相似（疑似拼写错误）。"""
    match = _NAME_ERROR_RE.search(ctx.stderr + '\n' + ctx.error_message)
    if not match:
        return False
    missing = match.group(1)
    for name in defined_names:
        if name != missing and _similar(missing, name) >= 0.6:
            return True
    return False


def _syntax_hint(code: str, stderr: str) -> tuple[bool, str]:
    """尝试解析代码，返回 (是否语法错误, 细分提示)。"""
    blob = stderr.lower()
    if 'indentationerror' in blob or 'taberror' in blob:
        return True, 'indentation'
    try:
        ast.parse(code)
    except SyntaxError as exc:
        msg = (exc.msg or '').lower()
        text = (exc.text or '')
        stripped = text.strip()
        # 缺冒号：行以 if/for/while/def/elif/else/try/except 开头但不以 : 结尾
        if re.match(r'^(if|for|while|def|elif|else|try|except|class|with|finally)\b', stripped) \
                and not stripped.rstrip().endswith(':'):
            return True, 'missing_colon'
        if 'expected \':\'' in msg or 'expected :' in msg:
            return True, 'missing_colon'
        if 'indent' in msg:
            return True, 'indentation'
        return True, 'generic'
    except Exception:
        # 非 SyntaxError 的解析异常，保守判断
        if 'syntaxerror' in blob:
            return True, 'generic'
        return False, ''
    if 'syntaxerror' in blob:
        return True, 'generic'
    return False, ''


def _analyze_ast(code: str) -> dict:
    """遍历 AST 收集循环 / 累加 / 条件相关信号。"""
    signals = {
        'has_loop': False,
        'has_while': False,
        'has_for': False,
        'uses_range': False,
        'uses_input': False,
        'while_no_update': False,
        'accumulator_use_before_init': False,
        'condition_suspect': False,
        'defined_names': set(),
        'called_funcs': set(),
    }
    try:
        tree = ast.parse(code)
    except Exception:
        # 解析失败：用字符串兜底
        low = code.lower()
        signals['has_loop'] = 'for ' in low or 'while ' in low
        signals['has_for'] = 'for ' in low
        signals['has_while'] = 'while ' in low
        signals['uses_range'] = 'range(' in low
        signals['uses_input'] = 'input(' in low
        return signals

    assigned_before: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_For(self, node: ast.For) -> None:
            signals['has_loop'] = True
            signals['has_for'] = True
            self.generic_visit(node)

        def visit_While(self, node: ast.While) -> None:
            signals['has_loop'] = True
            signals['has_while'] = True
            # 收集 while 条件里用到的变量名
            cond_names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
            # 循环体内被赋值 / 自增的变量名
            updated: set[str] = set()
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Assign):
                    for tgt in stmt.targets:
                        updated |= {n.id for n in ast.walk(tgt) if isinstance(n, ast.Name)}
                elif isinstance(stmt, ast.AugAssign):
                    updated |= {n.id for n in ast.walk(stmt.target) if isinstance(n, ast.Name)}
            # 条件里有变量，但循环体内没有任何条件变量被更新，且条件不是常量 True
            is_const_true = isinstance(node.test, ast.Constant) and bool(node.test.value)
            if (cond_names and not (cond_names & updated)) or is_const_true:
                # 排除有 break 的情况
                has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                if not has_break:
                    signals['while_no_update'] = True
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                signals['called_funcs'].add(node.func.id)
                if node.func.id == 'range':
                    signals['uses_range'] = True
                elif node.func.id == 'input':
                    signals['uses_input'] = True
            self.generic_visit(node)

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Store):
                signals['defined_names'].add(node.id)
                assigned_before.add(node.id)
            self.generic_visit(node)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            # a += ... 若 a 此前未普通赋值过，疑似累加未初始化
            if isinstance(node.target, ast.Name):
                name = node.target.id
                if name not in assigned_before:
                    signals['accumulator_use_before_init'] = True
                signals['defined_names'].add(name)
            self.generic_visit(node)

    Visitor().visit(tree)
    return signals


def analyze(ctx: DiagnosisContext) -> dict:
    """对外入口：返回供 rules 匹配的信号字典。"""
    signals = _analyze_ast(ctx.code)

    syntax_error, syntax_hint = _syntax_hint(ctx.code, ctx.stderr + '\n' + ctx.error_message)
    signals['syntax_error'] = syntax_error
    signals['syntax_hint'] = syntax_hint

    defined = signals.get('defined_names') or set()
    signals['name_typo'] = _detect_name_typo(ctx, defined)

    # off-by-one：用了 range 且有预期输出不一致
    signals['off_by_one'] = bool(signals.get('uses_range') and ctx.output_mismatch)
    signals['infinite_loop_risk'] = signals.get('while_no_update', False)

    # 条件可疑：有 if 且输出不一致（粗启发式，交给 logic 兜底规则）
    low = ctx.code.lower()
    signals['condition_suspect'] = ('if ' in low) and ctx.output_mismatch

    # 把 set 转为可序列化结构（仅保留长度 / 标记，避免污染 JSON）
    signals['defined_names'] = sorted(defined)
    signals['called_funcs'] = sorted(signals.get('called_funcs') or set())
    return signals
