"""Fail CI on likely committed credentials while allowing documented placeholders."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = (
    re.compile(r'IFLYTEK_SPARK_API_PASSWORD[ \t]*=[ \t]*[^\s#]+'),
    re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
    re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
)
ALLOWED = {'backend/.env.example'}


def main() -> int:
    names = subprocess.check_output(
        ['git', 'ls-files'],
        cwd=ROOT,
        text=True,
        encoding='utf-8',
    ).splitlines()
    findings = []
    for name in names:
        if name in ALLOWED:
            continue
        path = ROOT / name
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f'{name}: {pattern.pattern}')
    if findings:
        print('\n'.join(findings))
        return 1
    print('secret scan passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
