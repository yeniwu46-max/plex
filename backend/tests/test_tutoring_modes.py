"""Mode behavior, semantic failures, owned history and idempotent publication."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text

from test_learner_state import app
from test_tutor_context import headers, formal_body, run_result
from app.models import db, TrialQuestion
from app.models.learner_state import TutorDisplayReceipt, LearningEvent
from app.models.tutor_session import TutorSession, TutorTurn
from app.services.tutoring import TutorService
from app.services.tutor_context import TutorContextService, TutorContextError
from app.services.tutor_sessions import TutorSessions
from app.services.learner_state import fingerprint
from app.utils.time import utc_now


SOURCE = {'chunk_id': 'public-chunk', 'version': 2, 'title': '循环边界', 'document_id': 'public-doc',
          'url': '/api/v1/rag/sources/public-chunk?version=2', 'content': 'range 的停止值不包含在生成结果中。'}
EVIDENCE = {'status': 'grounded', 'sources': [SOURCE], 'prerequisite_gaps': []}
APPROVED = dict(answer_leakage=False, unsupported_claims=False, citation_mismatch=False,
                repeats_hint=False, policy_violation=False)


def body(app, mode='next_step', **extra):
    return {'request_id': str(uuid.uuid4()), 'mode': mode, 'hint_level': 4,
            'formal_question_id': app.config['TEST_QUESTION'], 'code': 'print(value)',
            'question': '我想核对循环的边界条件', **extra}


def candidate(mode='next_step'):
    result = {'summary': '先区分循环起点和停止条件。', 'next_step': '请写出停止条件何时成立。',
              'follow_up': '你如何核对边界？', 'citations': [{'chunk_id': SOURCE['chunk_id'], 'supports': '停止值的含义'}]}
    if mode in {'explain_error', 'review_approach'}:
        result['annotations'] = [{'line': 1, 'message': '核对这里使用的名称是否已定义。'}]
    if mode == 'pseudocode':
        result.update(scope='partial', pseudocode_lines=[{'step': '如果［待填写条件］成立', 'explanation': '这里只描述边界检查，不补全循环逻辑。'}])
    return result


class Provider:
    name = 'test-provider'
    def __init__(self, generated, review=None, callback=None):
        self.generated, self.review, self.callback = generated, APPROVED if review is None else review, callback
        self.calls = []
    def available(self): return True
    def generate_json(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) % 2:
            if self.callback: self.callback()
            return deepcopy(self.generated)
        return deepcopy(self.review)


@pytest.fixture
def dependencies(app):
    app.config['TUTOR_MODELS_ENABLED'] = True
    with patch('app.services.tutoring.KnowledgeService.tutor_evidence', return_value=deepcopy(EVIDENCE)) as evidence, \
         patch('app.services.tutoring.KnowledgeService.tutor_sources_current', return_value=True) as access:
        yield evidence, access


def ask(app, payload, provider):
    with patch('app.services.tutoring.get_llm_provider', return_value=provider):
        return app.test_client().post('/api/v1/student/tutor/ask', headers=headers(app), json=payload)


@pytest.mark.parametrize('mode', ['explain_error', 'review_approach', 'next_step', 'pseudocode'])
def test_each_mode_uses_its_contract_same_state_and_owned_context(app, dependencies, mode):
    payload = body(app, mode)
    if mode == 'explain_error':
        with patch('app.services.code_execution.CodeExecutionService.run', return_value=run_result()):
            run = app.test_client().post('/api/v1/code/run', headers=headers(app), json=payload).json['data']
        payload['run_id'] = run['run_id']
    provider = Provider(candidate(mode))
    response = ask(app, payload, provider)
    assert response.status_code == 200
    data = response.json['data']
    assert data['status'] == 'ok' and data['mode'] == mode and data['teaching_plan']['hint_level'] == 2
    assert data['state_version'] == data['teaching_plan']['decision']['state_version']
    assert data['citations'][0]['url'] == SOURCE['url'] and 'content' not in data['citations'][0]
    assert ('pseudocode_lines' in data) == (mode == 'pseudocode')
    assert ('annotations' in data) == (mode in {'explain_error', 'review_approach'})
    assert len(provider.calls) == 2
    assert 'correct_index' not in provider.calls[0]['user'] and 'age_range' not in provider.calls[0]['user']
    assert dependencies[0].call_args.kwargs['state_snapshot']['state_version'] == data['state_version']


def test_missing_run_asks_for_context_without_generation_or_receipt(app, dependencies):
    provider = Provider(candidate('explain_error'))
    data = ask(app, body(app, 'explain_error'), provider).json['data']
    assert data['status'] == 'needs_context' and data['display_receipt_id'] is None
    assert not provider.calls and not dependencies[0].called


@pytest.mark.parametrize('mode', [[], {}, None, 'invented'])
def test_invalid_modes_are_request_errors_without_creating_turns(app, dependencies, mode):
    assert ask(app, body(app, mode), Provider(candidate())).status_code == 400
    with app.app_context(): assert TutorTurn.query.count() == 0


def test_mode_button_label_is_not_treated_as_a_student_approach(app, dependencies):
    provider = Provider(candidate('review_approach'))
    data = ask(app, body(app, 'review_approach', code='', question='检查我的思路'), provider).json['data']
    assert data['status'] == 'needs_context' and not provider.calls


@pytest.mark.parametrize('failure', ['line', 'source', 'url', 'extra', 'full_algorithm', 'false_execution', 'bad_review'])
def test_invalid_or_semantically_unsafe_candidates_never_publish_or_persist(app, dependencies, failure):
    generated, review = candidate('review_approach'), dict(APPROVED)
    marker = 'UNSAFE-CANDIDATE'
    generated['summary'] = marker
    if failure == 'line': generated['annotations'][0]['line'] = 80
    if failure == 'source': generated['citations'][0]['chunk_id'] = 'invented'
    if failure == 'url': generated['citations'][0]['url'] = 'https://attacker.invalid'
    if failure == 'extra': generated['hidden_solution'] = 'print(2)'
    if failure == 'full_algorithm': review['answer_leakage'] = True
    if failure == 'false_execution': review['unsupported_claims'] = True
    if failure == 'bad_review': review = {'answer_leakage': 'false'}
    data = ask(app, body(app, 'review_approach'), Provider(generated, review)).json['data']
    assert data['status'] == 'safe_fallback' and marker not in str(data)
    assert data['display_receipt_id'] is None
    with app.app_context():
        assert marker not in str(TutorTurn.query.one().response)
        assert TutorDisplayReceipt.query.count() == 0


def test_retry_returns_identical_response_and_one_display_event(app, dependencies):
    payload, provider = body(app), Provider(candidate())
    first = ask(app, payload, provider).json['data']
    second = ask(app, payload, provider).json['data']
    assert first == second and len(provider.calls) == 2
    changed = ask(app, {**payload, 'code': 'print(another_value)'}, provider)
    assert changed.status_code == 409
    client, auth = app.test_client(), headers(app)
    url = '/api/v1/student/tutor-responses/' + first['display_receipt_id'] + '/displayed'
    assert client.post(url, headers=auth).status_code == 200
    assert client.post(url, headers=auth).status_code == 200
    with app.app_context():
        assert TutorTurn.query.count() == TutorDisplayReceipt.query.count() == 1
        assert LearningEvent.query.filter_by(kind='hint_displayed').count() == 1


def test_acknowledged_history_prevents_repeated_hint_and_stays_task_scoped(app, dependencies):
    first = ask(app, body(app), Provider(candidate())).json['data']
    client, auth = app.test_client(), headers(app)
    client.post('/api/v1/student/tutor-responses/' + first['display_receipt_id'] + '/displayed', headers=auth)
    provider = Provider(candidate())
    result = ask(app, body(app, session_id=first['session_id']), provider).json['data']
    assert result['policy_result']['reason'] == 'repeated_hint'
    assert result['next_step'] != first['next_step'] and len(provider.calls) == 1
    request = json.loads(provider.calls[0]['user'])
    assert request['displayed_history'][0]['next_step'] == first['next_step']
    unrelated = body(app, formal_question_id=None, question_ref='hello-print', session_id=first['session_id'])
    assert ask(app, unrelated, Provider(candidate())).status_code == 409
    with app.app_context():
        db.session.get(TutorSession, first['session_id']).user_id = app.config['TEST_TEACHER']; db.session.commit()
    assert ask(app, body(app, session_id=first['session_id']), Provider(candidate())).status_code == 404


def test_unacknowledged_or_revoked_history_not_sent_to_model(app, dependencies):
    first = ask(app, body(app), Provider(candidate())).json['data']
    generated = candidate(); generated['next_step'] = '请明确你要检查的输入范围。'
    provider = Provider(generated)
    ask(app, body(app, session_id=first['session_id']), provider)
    assert not json.loads(provider.calls[0]['user'])['displayed_history']


def test_revocation_after_generation_discards_all_content_and_cache_rechecks(app, dependencies):
    payload = body(app)
    first = ask(app, payload, Provider(candidate())).json['data']
    client, auth = app.test_client(), headers(app)
    read_url = '/api/v1/student/tutor/turns/' + payload['request_id']
    assert client.get(read_url, headers=auth).json['data'] == first
    assert client.get(read_url, headers=headers(app, teacher=True)).status_code == 403
    dependencies[1].return_value = False
    assert client.get(read_url, headers=auth).status_code == 409
    assert ask(app, payload, Provider(candidate())).status_code == 409
    fresh = body(app)
    assert ask(app, fresh, Provider(candidate())).status_code == 409
    with app.app_context():
        assert db.session.get(TutorTurn, fresh['request_id']).status == 'failed'
        assert TutorDisplayReceipt.query.count() == 1


def test_policy_changed_during_model_call_discards_response(app, dependencies):
    def withdraw():
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        q.trial.tutoring_policy = 'disabled'; db.session.commit()
    response = ask(app, body(app), Provider(candidate(), callback=withdraw))
    assert response.status_code == 409
    with app.app_context(): assert TutorDisplayReceipt.query.count() == 0


def test_concept_only_removes_task_code_and_rejects_annotations(app, dependencies):
    with app.app_context():
        q = db.session.get(TrialQuestion, app.config['TEST_QUESTION'])
        q.trial.tutoring_policy = 'concept_only'; db.session.commit()
    provider = Provider(candidate('review_approach'))
    data = ask(app, body(app, 'review_approach'), provider).json['data']
    sent = json.loads(provider.calls[0]['user'])
    assert sent['student_code'] == '' and sent['execution'] is None
    assert set(sent['task']) == {'concept_id'}
    assert data['status'] == 'safe_fallback' and data['teaching_plan']['hint_level'] == 1


def test_retrieval_failure_is_explicit_and_no_model_is_enabled_in_tests_by_default(app, dependencies):
    dependencies[0].side_effect = RuntimeError('vector failure')
    app.config['TUTOR_MODELS_ENABLED'] = False
    provider = Provider(candidate())
    result = ask(app, body(app), provider).json['data']
    assert result['evidence_status'] == 'retrieval_unavailable' and result['citations'] == []
    assert result['generation_mode'] == 'rules' and not provider.calls


def test_same_request_concurrent_claim_and_expired_worker_cannot_publish(app):
    payload = body(app)
    def claim():
        with app.app_context():
            try:
                context = TutorContextService.resolve(app.config['TEST_STUDENT'], payload)
                return TutorSessions.claim(app.config['TEST_STUDENT'], payload['request_id'], None,
                    fingerprint(payload), context, payload['question'], payload['mode'])
            except TutorContextError as exc:
                return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(), range(2)))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 409 in results
    old = next(r for r in results if isinstance(r, dict))
    with app.app_context():
        context = TutorContextService.resolve(app.config['TEST_STUDENT'], payload)
        turn = db.session.get(TutorTurn, payload['request_id']); turn.lease_until = utc_now() - timedelta(seconds=1)
        db.session.get(TutorSession, turn.session_id).lease_until = turn.lease_until; db.session.commit()
        new = TutorSessions.claim(app.config['TEST_STUDENT'], payload['request_id'], None,
            fingerprint(payload), context, payload['question'], payload['mode'])
        assert old['token'] != new['token']
        with pytest.raises(TutorContextError):
            TutorSessions.finish(app.config['TEST_STUDENT'], old, {}, context, count_help=False, dependencies=[])
        assert TutorDisplayReceipt.query.count() == 0


def test_tutor_migration_preserves_active_data_on_repeat(app):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    file = Path(__file__).resolve().parents[1] / 'migrations/versions/20261016_0022_tutor_sessions.py'
    spec = importlib.util.spec_from_file_location('tutor_sessions_migration', file)
    migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
    with app.app_context(), db.engine.begin() as conn:
        migration.op = Operations(MigrationContext.configure(conn))
        migration.upgrade(); migration.upgrade()
        assert conn.execute(text('SELECT COUNT(*) FROM tutor_turns')).scalar() == 0
