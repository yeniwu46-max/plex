"""The optional CrewAI path must honor the shared no-external-model test gate."""
from unittest.mock import patch

from flask import Flask
import pytest

# Production imports initialize app before agents; preserve that bootstrap order.
from app import create_app  # noqa: F401
from agents import crew


@pytest.mark.parametrize('backend', ['auto', 'crewai'])
def test_disabled_test_models_never_probe_or_launch_crewai(monkeypatch, backend):
    monkeypatch.setenv('AGENT_BACKEND', backend)
    app = Flask(__name__)
    app.config.update(TESTING=True, LLM_ALLOW_IN_TESTS=False)
    with app.app_context(), \
         patch.object(crew, '_crewai_available', side_effect=AssertionError('must not import CrewAI')), \
         patch.object(crew, '_run_crewai_subprocess', side_effect=AssertionError('must not launch child')):
        assert crew.backend_name() == 'mock'
        assert crew._try_crewai_student_pipeline({'code': 'synthetic fixture'}) is None


@pytest.mark.parametrize('testing,opt_in', [(True, True), (False, False)])
def test_explicit_model_opt_in_and_production_keep_backend_selection(monkeypatch, testing, opt_in):
    monkeypatch.setenv('AGENT_BACKEND', 'crewai')
    app = Flask(__name__)
    app.config.update(TESTING=testing, LLM_ALLOW_IN_TESTS=opt_in)
    with app.app_context(), patch.object(crew, '_crewai_available', return_value=True) as probe:
        assert crew.backend_name() == 'crewai'
        probe.assert_called_once()
