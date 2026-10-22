"""Regression for contradictory growth cards discovered in browser acceptance."""
from unittest.mock import patch

from app.models import db, TrialQuestion, StudentMistake, User
from app.services.assignment import AssignmentService
from app.services.student_progress import StudentProgressService
from app.services.learner_state import LearnerStateService as State
from test_learner_state import app, append


def test_growth_has_no_level_derived_mastery_and_keeps_all_domains(app):
    with app.app_context():
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        uid = app.config['TEST_STUDENT']
        db.session.get(User, uid).level = 100
        db.session.commit()
        empty = StudentProgressService.get_archive_insights(uid)
        assert empty['state_version'] == 0 and empty['state_source'] == 'evidence'
        assert len(empty['skills']) == 8
        assert all(s['percent'] is None and s['formal_attempts'] == 0 for s in empty['skills'])
        append(app, 'one', correct=False); append(app, 'two', correct=False)
        db.session.commit(); State.drain()
        result = StudentProgressService.get_archive_insights(uid)
        assert result['state_version'] == 2
        loop = next(s for s in result['skills'] if s['key'] == 'loop')
        assert loop['percent'] == 25 and loop['observed_concepts'] == 1
        assert loop['total_concepts'] > 1 and loop['formal_attempts'] == 2
        assert all(s['percent'] is None for s in result['skills'] if s['key'] != 'loop')


def test_failed_formal_code_keeps_concept_title_and_runtime_cause(app):
    with app.app_context():
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        q.question_type = 'coding'; q.knowledge_key = 'loop-for'
        q.stem = '循环中的边界：求和'
        q.set_coding_meta({'test_cases': [{'input': '1 2', 'expected': '3'}]})
        db.session.commit()
        result = {'all_passed': False, 'passed_count': 0, 'total': 1, 'backend': 'docker',
                  'results': [{'passed': False, 'error': 'IndexError', 'actual': '', 'status': 11}]}
        with patch('app.services.code_execution.CodeExecutionService.submit', return_value=result), \
             patch('app.services.grading_orchestrator.GradingOrchestrator.run_after_submit', return_value=[]):
            AssignmentService.submit_code_answer(app.config['TEST_STUDENT'], q.id, 'print(data[9])')
        row = StudentMistake.query.filter_by(user_id=app.config['TEST_STUDENT'], source='code_trial').one()
        assert row.knowledge_key == 'loop-for'
        assert row.question_title == q.stem
        assert row.error_type == 'runtime_error'
        assert row.meta['knowledge_label'] == 'for 与 range'
        assert row.meta['error_types'] == ['runtime_error']
