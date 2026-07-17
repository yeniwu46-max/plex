"""Subprocess wrappers for static analysis and runtime checks."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.services.code_execution import CodeExecutionService

DEFAULT_TIMEOUT = 10
_SUBPROCESS_KW = {
    'capture_output': True,
    'text': True,
    'encoding': 'utf-8',
    'errors': 'replace',
}


def _run_command(args: list[str], cwd: Path, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            timeout=timeout,
            **_SUBPROCESS_KW,
        )
        output = (proc.stdout or '') + (proc.stderr or '')
        return {
            'available': True,
            'returncode': proc.returncode,
            'output': output.strip()[:2000],
            'passed': proc.returncode == 0,
        }
    except FileNotFoundError:
        return {'available': False, 'returncode': None, 'output': '', 'passed': None}
    except subprocess.TimeoutExpired:
        return {'available': True, 'returncode': -1, 'output': 'Command timed out', 'passed': False}


def _tool_module(module: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, '-m', module, '--version'],
            timeout=5,
            **_SUBPROCESS_KW,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def compile_python(source: str, label: str = 'snippet') -> dict[str, Any]:
    try:
        compile(source, f'<{label}>', 'exec')
        return {'available': True, 'passed': True, 'output': ''}
    except SyntaxError as exc:
        return {'available': True, 'passed': False, 'output': str(exc)}


def run_static_suite(sources: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Run compile + optional ruff/black/mypy/bandit on extracted code blocks."""
    results: list[dict[str, Any]] = []
    if not sources:
        results.append({
            'tool': 'compile',
            'level': 'WARNING',
            'detail': '资源包中未找到可检查的 Python 代码',
        })
        return results

    with tempfile.TemporaryDirectory(prefix='plex_audit_') as tmp:
        root = Path(tmp)
        for index, (label, source) in enumerate(sources):
            path = root / f'{index}_{label}.py'
            path.write_text(source, encoding='utf-8')

            comp = compile_python(source, label)
            results.append({
                'tool': 'compile',
                'file': path.name,
                'level': 'PASS' if comp['passed'] else 'FAIL',
                'detail': comp['output'] or '语法检查通过',
            })

        if _tool_module('ruff'):
            ruff = _run_command([sys.executable, '-m', 'ruff', 'check', '.'], root)
            results.append({
                'tool': 'ruff',
                'level': 'PASS' if ruff['passed'] else 'WARNING',
                'detail': ruff['output'] or 'Ruff 检查通过',
            })
        elif ruff_bin := shutil.which('ruff'):
            ruff = _run_command([ruff_bin, 'check', '.'], root)
            results.append({
                'tool': 'ruff',
                'level': 'PASS' if ruff['passed'] else 'WARNING',
                'detail': ruff['output'] or 'Ruff 检查通过',
            })
        else:
            results.append({
                'tool': 'ruff',
                'level': 'WARNING',
                'detail': 'Ruff 未安装，已跳过（可 pip install -r requirements-audit.txt）',
            })

        if _tool_module('black'):
            black = _run_command([sys.executable, '-m', 'black', '--check', '.'], root)
            results.append({
                'tool': 'black',
                'level': 'PASS' if black['passed'] else 'WARNING',
                'detail': black['output'] or 'Black 格式检查通过',
            })
        else:
            results.append({
                'tool': 'black',
                'level': 'WARNING',
                'detail': 'Black 未安装，已跳过',
            })

        if _tool_module('mypy'):
            mypy = _run_command(
                [sys.executable, '-m', 'mypy', '--ignore-missing-imports', '.'],
                root,
            )
            results.append({
                'tool': 'mypy',
                'level': 'PASS' if mypy['passed'] else 'WARNING',
                'detail': mypy['output'] or 'mypy 类型检查通过',
            })
        else:
            results.append({
                'tool': 'mypy',
                'level': 'WARNING',
                'detail': 'mypy 未安装，已跳过',
            })

        if _tool_module('bandit'):
            bandit = _run_command([sys.executable, '-m', 'bandit', '-r', '-q', '.'], root)
            results.append({
                'tool': 'bandit',
                'level': 'PASS' if bandit['passed'] else 'WARNING',
                'detail': bandit['output'] or 'Bandit 安全检查通过',
            })
        elif bandit_bin := shutil.which('bandit'):
            bandit = _run_command([bandit_bin, '-r', '-q', '.'], root)
            results.append({
                'tool': 'bandit',
                'level': 'PASS' if bandit['passed'] else 'WARNING',
                'detail': bandit['output'] or 'Bandit 安全检查通过',
            })
        else:
            results.append({
                'tool': 'bandit',
                'level': 'WARNING',
                'detail': 'Bandit 未安装，已跳过',
            })

    return results


def run_runtime_checks(sources: list[tuple[str, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for label, source in sources:
        stripped = source.strip()
        if not stripped or stripped.startswith('#'):
            continue
        run_result = CodeExecutionService.run('python3', stripped)
        status_id = run_result.get('status', {}).get('id')
        if status_id == 3:
            level = 'PASS'
            detail = '运行成功'
        elif status_id == 5:
            level = 'FAIL'
            detail = '运行超时，可能存在死循环'
        else:
            level = 'WARNING'
            detail = (
                run_result.get('stderr')
                or run_result.get('compile_output')
                or run_result.get('status', {}).get('description', '运行失败')
            )
        results.append({'tool': 'runtime', 'file': label, 'level': level, 'detail': str(detail)[:500]})
    return results


def run_pytest_if_present(source: str, label: str) -> dict[str, Any] | None:
    if 'def test_' not in source:
        return None
    if not _tool_module('pytest'):
        return {
            'tool': 'pytest',
            'level': 'WARNING',
            'detail': 'pytest 未安装，已跳过测试执行',
        }
    with tempfile.TemporaryDirectory(prefix='plex_pytest_') as tmp:
        path = Path(tmp) / f'{label}.py'
        path.write_text(source, encoding='utf-8')
        result = _run_command([sys.executable, '-m', 'pytest', '-q', str(path)], Path(tmp))
        return {
            'tool': 'pytest',
            'level': 'PASS' if result['passed'] else 'WARNING',
            'detail': result['output'] or 'pytest 通过',
        }
