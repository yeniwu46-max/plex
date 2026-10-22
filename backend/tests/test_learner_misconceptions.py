"""Signals remain hypotheses; teacher corrections and subsequent evidence are audited."""
import uuid
from datetime import timedelta
from unittest.mock import patch
import pytest
from flask_jwt_extended import create_access_token
from app.models import db, User, LearningEvent, LearnerStateChange
from app.services.learner_state import LearnerStateService as State
from app.services.learner_decision import LearnerDecisionService as Decision
from app.services.misconception_policy import detect_signals, MisconceptionPolicy
from app.services.misconception_review import MisconceptionReviewService as Review, ReviewConflict
from app.utils.time import utc_now
from test_learner_state import app, snapshot

CODE = 'items = [1, 2, 3]\nfor i in range(len(items) - 1):\n    print(items[i])'


def event(app, question=101, *, correct=False, assisted=False, when=None, signal=True):
    return State.append(user_id=app.config['TEST_STUDENT'], kind='submission_graded',
        source_type='trial_question_progress', source_id=str(question), source_version='1', occurred_at=when,
        payload={'concept_id': 'loop', 'question_id': question, 'correct': correct, 'assisted': assisted,
                 'evidence_scope': 'server_graded', 'diagnostic_signals': detect_signals(CODE, {'code_passed': False}) if signal else []})


def candidate(app):
    event(app); db.session.commit(); assert State.drain() == 1
    return snapshot(app)['misconceptions'][0]


def review(app, row, action='confirm', **overrides):
    data = {'request_id': str(uuid.uuid4()), 'action': action, 'expected_revision': row['revision'], 'note': '已核对代码与失败输入'}
    data.update(overrides)
    return Review.review(app.config['TEST_TEACHER'], app.config['TEST_STUDENT'], row['id'], data), data


def test_signal_requires_failed_execution_and_does_not_claim_causation():
    assert not detect_signals(CODE, {'code_passed': True})
    assert not detect_signals(CODE, {})
    assert not detect_signals('print("syntax', {'code_passed': False})
    signal = detect_signals(CODE, {'code_passed': False})[0]
    assert signal['kind'] == 'loop_end_excluded' and '待核对' in signal['observation']
    recursive = 'def f(n):\n    return f(n - 1)'
    assert not detect_signals(recursive, {'code_passed': False})
    assert detect_signals(recursive, {'code_passed': False, 'results': [{'stderr': 'RecursionError'}]})[0]['kind'] == 'recursion_missing_guard'


def test_repeated_distinct_questions_remain_candidate_and_share_decision(app):
    with app.app_context():
        first = candidate(app)
        assert first['status'] == 'candidate' and first['distinct_questions'] == 1
        assert Decision.from_snapshot(snapshot(app))['basis'] == 'baseline'
        event(app, 102); event(app, 102); db.session.commit(); assert State.drain() == 1
        s = snapshot(app); row = s['misconceptions'][0]
        assert row['status'] == 'candidate' and row['distinct_questions'] == 2
        decision = Decision.from_snapshot(s)
        assert decision['basis'] == 'repeated_candidate'
        for part in ('hint', 'next_exercise', 'review'):
            assert decision[part]['state_version'] == s['state_version'] == 2
            assert set(decision[part]['evidence_ids']) == {e['event_id'] for e in row['evidence']}
            assert decision[part]['concept_id'] == decision['concept_id']
        # A recursion task must not inherit the unrelated loop diagnosis.
        assert Decision.from_snapshot(s, focus_concept='recursion')['basis'] == 'baseline'


def test_teacher_review_once_stale_conflict_and_no_ability_change(app):
    with app.app_context():
        row = candidate(app)
        reviewed, data = review(app, row)
        assert reviewed['state_version'] == 2 and reviewed['misconceptions'][0]['status'] == 'confirmed'
        repeated = Review.review(app.config['TEST_TEACHER'], app.config['TEST_STUDENT'], row['id'], data)
        assert repeated['state_version'] == 2 and LearningEvent.query.count() == 2
        assert repeated['concepts'][0]['independent_count'] == 1
        assert Decision.from_snapshot(repeated)['basis'] == 'confirmed_misconception'
        with pytest.raises(ReviewConflict): review(app, row, 'dismiss')
        db.session.rollback()
        with pytest.raises(ReviewConflict):
            Review.review(app.config['TEST_TEACHER'], app.config['TEST_STUDENT'], row['id'], {**data, 'action': 'dismiss'})
        db.session.rollback()
        assert snapshot(app)['state_version'] == 2 and LearningEvent.query.count() == 2


def test_teacher_review_failure_rolls_back_event_and_projection(app):
    with app.app_context():
        row = candidate(app)
        with patch.object(MisconceptionPolicy, 'apply', side_effect=ValueError('injected failure')):
            with pytest.raises(ValueError): review(app, row)
        db.session.rollback()
        assert snapshot(app)['misconceptions'][0]['status'] == 'candidate'
        assert LearningEvent.query.count() == LearnerStateChange.query.count() == 1


def test_dismissal_is_not_overridden_by_later_rules_and_reopen_is_audited(app):
    with app.app_context():
        row = candidate(app)
        reviewed, _ = review(app, row, 'dismiss')
        event(app, 102); db.session.commit(); State.drain()
        s = snapshot(app)
        assert s['misconceptions'][0]['status'] == 'dismissed'
        assert Decision.from_snapshot(s)['basis'] != 'repeated_candidate'
        s, _ = review(app, s['misconceptions'][0], 'reopen')
        assert s['misconceptions'][0]['status'] == 'candidate'
        assert s['state_version'] == 4


@pytest.mark.parametrize('reverse', [False, True])
def test_mitigation_uses_two_distinct_later_independent_successes_not_processing_order(app, reverse):
    with app.app_context():
        now = utc_now()
        producers = [lambda: event(app, 101, when=now - timedelta(days=3)),
                     lambda: event(app, 102, correct=True, signal=False, when=now - timedelta(days=2)),
                     lambda: event(app, 103, correct=True, signal=False, when=now - timedelta(days=1))]
        for producer in reversed(producers) if reverse else producers:
            producer(); db.session.commit(); State.drain()
        s = snapshot(app)
        assert s['misconceptions'][0]['status'] == 'mitigated'
        event(app, 104, when=now); db.session.commit(); State.drain()
        assert snapshot(app)['misconceptions'][0]['status'] == 'candidate'


def test_assisted_success_cannot_mitigate(app):
    with app.app_context():
        candidate(app)
        event(app, 102, correct=True, assisted=True, signal=False)
        event(app, 103, correct=True, signal=False)
        db.session.commit(); State.drain()
        assert snapshot(app)['misconceptions'][0]['status'] == 'candidate'


def test_review_endpoint_permissions_and_validation(app):
    with app.app_context():
        row = candidate(app)
        teacher, student = app.config['TEST_TEACHER'], app.config['TEST_STUDENT']
        tokens = {uid: {'Authorization': 'Bearer ' + create_access_token(identity=str(uid))} for uid in (teacher, student)}
    client = app.test_client()
    url = f'/api/v1/teacher/students/{student}/misconceptions/{row["id"]}/review'
    data = {'request_id': str(uuid.uuid4()), 'expected_revision': row['revision'], 'action': 'confirm', 'note': '核对终点'}
    assert client.post(url, headers=tokens[student], json=data).status_code == 403
    assert client.post(url, headers=tokens[teacher], json={**data, 'note': ' '}).status_code == 400
    assert client.post(url, headers=tokens[teacher], json=data).status_code == 200
    assert client.post(url, headers=tokens[teacher], json={**data, 'request_id': str(uuid.uuid4())}).status_code == 409
    with app.app_context():
        db.session.get(User, student).class_id = None; db.session.commit()
    assert client.post(url, headers=tokens[teacher], json=data).status_code == 403


def test_unknown_is_not_low_and_debug_error_not_confirmed_misconception(app):
    from app.services.knowledge.schemas import LearnerContext, QueryUnderstanding, GraphContext
    from app.services.knowledge.strategy_service import StrategyService
    with app.app_context():
        learner = LearnerContext(user_id=1)
        query = QueryUnderstanding('边界错了', '边界错了', intent='debug_error')
        graph = GraphContext(focus_ids=['loop-for'])
        strategy = StrategyService.select(query, learner, graph)
        assert strategy.mastery_band == 'unknown' and strategy.focus_mastery is None
        assert 'MISCONCEPTION_CORRECTION' not in strategy.strategies
        learner.misconceptions = [{'status': 'confirmed', 'concept_id': 'loop-for'}]
        assert 'MISCONCEPTION_CORRECTION' in StrategyService.select(query, learner, graph).strategies


def test_snapshot_consistent_when_new_event_processed_between_reads(app):
    from concurrent.futures import ThreadPoolExecutor
    with app.app_context():
        candidate(app)
        original = MisconceptionPolicy.serialize
        futures = []
        def writer():
            with app.app_context():
                event(app, 102); db.session.commit()
                assert State.drain() == 1
        with ThreadPoolExecutor(max_workers=1) as pool:
            def interleave(session, state_id):
                future = pool.submit(writer); futures.append(future)
                # MySQL permits the commit while the reader retains its MVCC
                # snapshot. SQLite rollback-journal holds the writer until read ends.
                if db.engine.dialect.name == 'mysql':
                    future.result(timeout=15)
                return original(session, state_id)
            with patch.object(MisconceptionPolicy, 'serialize', side_effect=interleave):
                s = snapshot(app)
            futures[0].result(timeout=15)
        assert s['state_version'] == 1 and s['misconceptions'][0]['distinct_questions'] == 1
        fresh = snapshot(app)
        assert fresh['state_version'] == 2 and fresh['misconceptions'][0]['distinct_questions'] == 2


def test_concurrent_teacher_reviews_conflict_instead_of_overwriting(app):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    with app.app_context():
        row = candidate(app)
    barrier = Barrier(2)
    def decide(action):
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                review(app, row, action)
                return 'saved'
            except ReviewConflict:
                db.session.rollback()
                return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(decide, ['confirm', 'dismiss'])) == ['conflict', 'saved']
    with app.app_context():
        assert snapshot(app)['state_version'] == 2
        assert LearningEvent.query.count() == 2


@pytest.mark.parametrize('signals', [[None], {'kind': 'loop_end_excluded'}, [dict(kind='not_known')]])
def test_malformed_diagnostic_evidence_is_quarantined(app, signals):
    with app.app_context():
        row = event(app)
        row.payload = {**row.payload, 'diagnostic_signals': signals}
        db.session.commit()
        assert State.drain() == 0
        assert snapshot(app)['state_version'] == 0
        assert LearningEvent.query.one().status == 'failed'
