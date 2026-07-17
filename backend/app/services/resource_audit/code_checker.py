"""Step 5: code quality checks."""
from __future__ import annotations

from .code_tools import run_pytest_if_present, run_runtime_checks, run_static_suite
from .schema import CheckItem, StepResult


def _extract_sources(bundle: dict) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    for index, block in enumerate(bundle.get('code') or []):
        if not isinstance(block, dict):
            continue
        src = str(block.get('source') or '').strip()
        if src:
            label = str(block.get('title') or f'code_{index}')
            sources.append((label, src))
    for index, ex in enumerate(bundle.get('exercises') or []):
        if not isinstance(ex, dict) or ex.get('type') != 'coding':
            continue
        src = str(ex.get('answer') or '').strip()
        if src:
            sources.append((f'exercise_{index}', src))
    return sources


def _tool_results_to_checks(tool_results: list[dict]) -> list[CheckItem]:
    checks: list[CheckItem] = []
    for row in tool_results:
        level = row.get('level', 'WARNING')
        tool = row.get('tool', 'tool')
        file_name = row.get('file', '')
        label = f'{tool}' + (f' ({file_name})' if file_name else '')
        checks.append(CheckItem(
            f'code_{tool}_{file_name or "all"}'.replace(' ', '_'),
            label,
            level,
            str(row.get('detail') or ''),
        ))
    return checks


def check_code(bundle: dict, knowledge_key: str) -> StepResult:
    del knowledge_key
    sources = _extract_sources(bundle)
    tool_results = run_static_suite(sources)
    tool_results.extend(run_runtime_checks(sources))
    for label, source in sources:
        pytest_result = run_pytest_if_present(source, label)
        if pytest_result:
            tool_results.append(pytest_result)

    checks = _tool_results_to_checks(tool_results)
    if not checks:
        checks.append(CheckItem('code_empty', '代码块', 'WARNING', '未找到可执行代码'))

    score = 100
    for check in checks:
        if check.level == 'FAIL':
            score -= 25
        elif check.level == 'WARNING':
            score -= 8
    score = max(0, min(100, score))

    has_fail = any(c.level == 'FAIL' for c in checks)
    summary = '代码质量良好' if score >= 80 and not has_fail else '代码存在语法或运行风险'
    return StepResult(step=5, name='代码质量', checks=checks, score=score, summary=summary)
