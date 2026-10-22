"""Run arrival contract tests in a disposable MySQL schema, never application data.

Uses the local DevelopmentConfig connection; requires CREATE/DROP DATABASE.
"""
import os
from pathlib import Path
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import DevelopmentConfig


def main():
    url = make_url(DevelopmentConfig.SQLALCHEMY_DATABASE_URI)
    if url.get_backend_name() != 'mysql':
        raise SystemExit('Configure a local MySQL development connection first.')
    name = 'plex_onboarding_test_' + uuid.uuid4().hex[:12]
    engine = create_engine(url.set(database=None), echo=False)
    with engine.begin() as connection:
        connection.execute(text('CREATE DATABASE `' + name + '` CHARACTER SET utf8mb4'))
    previous = os.environ.get('PLEX_ONBOARDING_TEST_MYSQL_SCHEMA')
    try:
        os.environ['PLEX_ONBOARDING_TEST_MYSQL_SCHEMA'] = name
        import pytest
        return pytest.main([str(ROOT / 'tests/test_onboarding.py'), '-q', '--disable-warnings'])
    finally:
        if previous is None:
            os.environ.pop('PLEX_ONBOARDING_TEST_MYSQL_SCHEMA', None)
        else:
            os.environ['PLEX_ONBOARDING_TEST_MYSQL_SCHEMA'] = previous
        with engine.begin() as connection:
            connection.execute(text('DROP DATABASE `' + name + '`'))
        engine.dispose()


if __name__ == '__main__':
    sys.exit(main())
