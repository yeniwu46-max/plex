"""Run evidence contracts in a randomly named, disposable MySQL database only."""
import os
import re
import sys
import uuid
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import DevelopmentConfig


def main():
    url = make_url(DevelopmentConfig.SQLALCHEMY_DATABASE_URI)
    if url.get_backend_name() != 'mysql':
        raise SystemExit('Local MySQL connection required.')
    name = 'plex_state_test_' + uuid.uuid4().hex[:12]
    assert re.fullmatch(r'plex_state_test_[a-f0-9]{12}', name)
    engine = create_engine(url.set(database=None), echo=False)
    with engine.begin() as conn:
        conn.execute(text('CREATE DATABASE `' + name + '` CHARACTER SET utf8mb4'))
    previous = os.environ.get('PLEX_STATE_TEST_MYSQL_SCHEMA')
    try:
        os.environ['PLEX_STATE_TEST_MYSQL_SCHEMA'] = name
        import pytest
        return pytest.main([str(ROOT / 'tests/test_learner_state.py'), str(ROOT / 'tests/test_learner_misconceptions.py'),
                            str(ROOT / 'tests/test_learning_decisions.py'),
                            str(ROOT / 'tests/test_knowledge_access.py'),
                            str(ROOT / 'tests/test_tutor_context.py'),
                            str(ROOT / 'tests/test_tutoring_modes.py'),
                            str(ROOT / 'tests/test_tutor_compat.py'),
                            str(ROOT / 'tests/test_messenger_tutoring.py'),
                            str(ROOT / 'tests/test_retrieval_quality.py'),
                            str(ROOT / 'tests/test_legacy_student_tutoring.py'),
                            str(ROOT / 'tests/test_learning_cycle.py'),
                            str(ROOT / 'tests/test_counterexample_gates.py'),
                            str(ROOT / 'tests/test_counterexample_attempts.py'),
                            str(ROOT / 'tests/test_counterexample_workbench.py'),
                            str(ROOT / 'tests/test_counterexample_generation.py'),
                            str(ROOT / 'tests/test_counterexample_properties.py'),
                            str(ROOT / 'tests/test_counterexample_catalog.py'),
                            str(ROOT / 'tests/test_resource_learning_context.py'),
                            str(ROOT / 'tests/test_resource_course_evidence.py'),
                            str(ROOT / 'tests/test_messenger_artifacts.py'),
                            str(ROOT / 'tests/test_tutor_runtime.py'),
                            str(ROOT / 'tests/test_model_accounting.py'),
                            str(ROOT / 'tests/test_resource_admission.py'),
                            str(ROOT / 'tests/test_rag_runtime.py'),
                            str(ROOT / 'tests/test_model_pricing.py'),
                            str(ROOT / 'tests/test_pilot_observability.py'),
                            str(ROOT / 'tests/test_learning_evidence.py'),
                            str(ROOT / 'tests/test_pdf_cleanup.py'),
                            str(ROOT / 'tests/test_python_trace.py'),
                            '-q', '--disable-warnings', *sys.argv[1:]])
    finally:
        if previous is None:
            os.environ.pop('PLEX_STATE_TEST_MYSQL_SCHEMA', None)
        else:
            os.environ['PLEX_STATE_TEST_MYSQL_SCHEMA'] = previous
        with engine.begin() as conn:
            conn.execute(text('DROP DATABASE `' + name + '`'))
        engine.dispose()


if __name__ == '__main__':
    sys.exit(main())
