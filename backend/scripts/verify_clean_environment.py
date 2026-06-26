"""Verify runtime, database, health, and demo-account readiness."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app


def command_version(command):
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except Exception:
        return None


def command_succeeds(command):
    try:
        return subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
    except Exception:
        return False


def run(output: Path) -> dict:
    app = create_app('development')
    client = app.test_client()
    accounts = {}
    for username, password in (
        ('student001', 'student123'),
        ('teacher001', 'teacher123'),
        ('admin', 'admin123'),
    ):
        response = client.post('/api/v1/auth/login', json={'username': username, 'password': password})
        accounts[username] = response.status_code == 200 and (response.get_json() or {}).get('code') == 0
    health_response = client.get('/api/v1/health')
    health = health_response.get_json() or {}
    with app.app_context():
        database_backend = app.extensions['sqlalchemy'].engine.dialect.name
    checks = {
        'python': {'passed': sys.version_info >= (3, 12), 'version': sys.version.split()[0]},
        'node': {'passed': shutil.which('node') is not None, 'version': command_version(['node', '--version'])},
        'npm': {
            'passed': shutil.which('npm') is not None,
            'version': command_version(['npm.cmd' if os.name == 'nt' else 'npm', '--version']),
        },
        'database': {
            'passed': health_response.status_code == 200,
            'backend': database_backend,
        },
        'health': {'passed': health_response.status_code == 200, 'response_code': health.get('code')},
        'demo_accounts': {'passed': all(accounts.values()), 'accounts': accounts},
    }
    report = {
        'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'passed': all(item['passed'] for item in checks.values()),
        'checks': checks,
        'external_conditions': {
            'docker': 'available' if shutil.which('docker') else 'blocked_local_tool_missing',
            'github_cli': (
                'authenticated'
                if shutil.which('gh') and command_succeeds(['gh', 'auth', 'status'])
                else 'blocked_not_authenticated'
                if shutil.which('gh')
                else 'blocked_local_tool_missing'
            ),
            'iflytek_spark': (
                'credential_configured'
                if os.getenv('IFLYTEK_SPARK_API_PASSWORD')
                else 'blocked_credential_missing'
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--output',
        type=Path,
        default=ROOT / 'reports/a3-next-stage/clean-environment.json',
    )
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
