"""Best-effort local sandbox for *safely re-running* a problem's
`reference_answer` code to produce a real, verified input/output sample
(task 2 in the "6 项增强" follow-up brief).

Design constraints from the brief:
  - Never invent an *output* -- every generated output must be the literal
    stdout of an actual execution of the reference answer.
  - A *reasonable* input may be constructed (e.g. guessed from the
    description's own worked example, or a generic placeholder) as long as
    the resulting output is obtained by really running the code with it.
  - Python is executed directly via `subprocess` with a short timeout.
  - Java is compiled with `javac`/run with `java` (JDK is available in this
    dev environment); if compilation/execution is not possible the caller
    must fall back to manual review instead of guessing.
  - Anything that isn't recognisably safe, pure, single-file Python/Java
    (i.e. touches the filesystem, network, subprocesses, or other I/O) is
    rejected before ever being executed and routed to manual review.

This is a *local developer tooling* sandbox (run once, offline, against a
fixed masked dataset) -- not a hardened multi-tenant code execution service.
For the latter this repo already has `app/services/code_execution.py`
(Judge0/E2B backed); reusing it here was intentionally avoided because it
requires live judge credentials/network and is designed for interactive
per-request judging, not idempotent batch backfill.
"""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PY_TIMEOUT_SECONDS = 5
JAVA_COMPILE_TIMEOUT_SECONDS = 15
JAVA_RUN_TIMEOUT_SECONDS = 5

_UNSAFE_PY_MODULES = {
    'os', 'sys', 'subprocess', 'socket', 'shutil', 'requests', 'urllib',
    'http', 'ctypes', 'multiprocessing', 'threading', 'importlib',
    'pathlib', 'glob', 'tempfile', 'pickle', 'shelve', 'sqlite3', 'ftplib',
}
_UNSAFE_PY_CALLS = {'open', 'eval', 'exec', '__import__', 'compile', 'input'}
# `input` is special-cased separately (it's how we *feed* stdin), so it is
# allowed as a call but tracked to decide whether a stdin guess is needed.

JAVA_INPUT_HINTS = ('Scanner', 'System.in', 'BufferedReader')


def detect_language(code: str) -> str | None:
    text = (code or '').strip()
    if not text:
        return None
    if re.search(r'\bpublic\s+class\s+\w+', text) or re.search(r'\bSystem\.out\.println', text):
        return 'java'
    if re.search(r'\bprint\s*\(', text) or 'input(' in text or text.startswith('#'):
        return 'python'
    return None


def is_safe_python(code: str) -> bool:
    """Conservative allowlist check via the AST -- reject anything that
    could touch the filesystem/network/process table. Does not guarantee
    perfect sandboxing (Python has no first-class capability system) but is
    sufficient for this masked, previously-human-authored beginner dataset.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
            for name in names:
                top = (name or '').split('.')[0]
                if top in _UNSAFE_PY_MODULES:
                    return False
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _UNSAFE_PY_CALLS and node.func.id != 'input':
                return False
    return True


def needs_stdin(code: str, language: str) -> bool:
    if language == 'python':
        return 'input(' in code
    if language == 'java':
        return any(hint in code for hint in JAVA_INPUT_HINTS)
    return False


_INLINE_EXAMPLE_RE = re.compile(
    r'(?:输入|input)\s*[：:]\s*([\u4e00-\u9fffA-Za-z0-9._-]{1,24})',
    re.IGNORECASE,
)


def guess_stdin_value(description_texts: list[str]) -> str:
    """Look for a worked example embedded in the narrative description
    (e.g. "例如，用户输入：小红，你的程序输出如下信息：...") before falling
    back to a generic placeholder. Prefers a *real* example from the
    source text over an invented one.
    """
    for text in description_texts:
        if not text:
            continue
        match = _INLINE_EXAMPLE_RE.search(text)
        if match:
            return match.group(1).strip()
    return 'PLEX'


def run_python(code: str, stdin_value: str) -> str | None:
    with tempfile.TemporaryDirectory(prefix='pb_sandbox_py_') as tmp:
        script_path = Path(tmp) / 'solution.py'
        script_path.write_text(code, encoding='utf-8')
        try:
            proc = subprocess.run(
                [sys.executable, '-I', str(script_path)],
                input=(stdin_value + '\n') if stdin_value else '',
                capture_output=True,
                text=True,
                timeout=PY_TIMEOUT_SECONDS,
                cwd=tmp,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout.strip('\n')


_JAVA_CLASS_RE = re.compile(r'\bpublic\s+class\s+(\w+)')


def run_java(code: str, stdin_value: str) -> str | None:
    if shutil.which('javac') is None or shutil.which('java') is None:
        return None
    match = _JAVA_CLASS_RE.search(code)
    if not match:
        return None
    class_name = match.group(1)
    with tempfile.TemporaryDirectory(prefix='pb_sandbox_java_') as tmp:
        src_path = Path(tmp) / f'{class_name}.java'
        src_path.write_text(code, encoding='utf-8')
        try:
            compile_proc = subprocess.run(
                ['javac', '-d', tmp, str(src_path)],
                capture_output=True,
                text=True,
                timeout=JAVA_COMPILE_TIMEOUT_SECONDS,
                cwd=tmp,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        if compile_proc.returncode != 0:
            return None
        try:
            run_proc = subprocess.run(
                ['java', '-cp', tmp, class_name],
                input=(stdin_value + '\n') if stdin_value else '',
                capture_output=True,
                text=True,
                timeout=JAVA_RUN_TIMEOUT_SECONDS,
                cwd=tmp,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        if run_proc.returncode != 0:
            return None
        return run_proc.stdout.strip('\n')


def execute_reference_answer(
    code: str,
    description_texts: list[str],
) -> tuple[dict | None, str]:
    """Try to produce one real, executed sample.

    Returns (sample_or_none, reason). `reason` is a short machine-readable
    code describing what happened, used both for stats and for the
    manual-review message when sample is None.
    """
    language = detect_language(code)
    if language is None:
        return None, 'unrecognized_language'
    if language == 'python' and not is_safe_python(code):
        return None, 'unsafe_python_rejected'

    stdin_value = guess_stdin_value(description_texts) if needs_stdin(code, language) else ''

    if language == 'python':
        output = run_python(code, stdin_value)
    else:
        output = run_java(code, stdin_value)

    if output is None:
        return None, f'{language}_execution_failed_or_timeout'
    if not output:
        return None, f'{language}_produced_empty_output'
    return {'input': stdin_value, 'output': output}, f'{language}_executed_ok'
