"""Verify a configured database is actually MySQL 8.x without exposing credentials."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]


def verify(database_url: str, output: Path) -> dict:
    report = {
        'benchmark': 'plex-mysql8-clean-environment',
        'run_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'database_url_present': bool(database_url),
        'database_url': re.sub(r'//([^:/]+):([^@]+)@', r'//\\1:<redacted>@', database_url),
        'backend': None,
        'version': None,
        'version_comment': None,
        'table_count': 0,
        'checks': {},
    }
    if not database_url:
        report['checks'] = {'configured': False, 'mysql_8': False, 'connectivity': False}
    else:
        engine = create_engine(database_url, pool_pre_ping=True)
        report['backend'] = engine.dialect.name
        with engine.connect() as connection:
            report['version'] = str(connection.execute(text('SELECT VERSION()')).scalar() or '')
            report['version_comment'] = str(connection.execute(text('SELECT @@version_comment')).scalar() or '')
            connection.execute(text('SELECT 1'))
        report['table_count'] = len(inspect(engine).get_table_names())
        report['checks'] = {
            'configured': True,
            'mysql_8': report['backend'] == 'mysql' and str(report['version']).startswith('8.'),
            'connectivity': True,
            'schema_present': report['table_count'] > 0,
        }
    report['passed'] = bool(report['checks'].get('mysql_8') and report['checks'].get('connectivity') and report['checks'].get('schema_present'))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database-url', default=os.getenv('DATABASE_URL', ''))
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/a3-next-stage/mysql-clean-environment.json')
    args = parser.parse_args()
    result = verify(args.database_url, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
