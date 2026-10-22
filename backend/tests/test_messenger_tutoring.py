"""Actual free-chat routes: intent, owned history, SSE publication and retries."""
import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from test_learner_state import app
from test_tutor_context import headers
from test_tutoring_modes import dependencies, Provider, candidate, APPROVED
from test_chat_stream import parse_sse
from app.models import db, TrialQuestion, TrialQuestionProgress
from app.models.tutor_session import TutorTurn
from app.models.learner_state import LearningEvent, TutorDisplayReceipt
from app.services.tutor_intents import infer_mode
from app.services.learner_state import LearnerStateService
from app.utils.time import utc_now


def message(text='什么是 Python 列表？', **extra):
    return {'message': text, 'request_id': str(uuid.uuid4()), **extra}


def generated(mode='concept_explain'):
    raw = candidate()
    if mode == 'concept_explain':
        raw.update(summary='列表按顺序保存元素，可以通过索引读取。', next_step='', follow_up='',
                   example={'code':'items = [1, 2]\nprint(items[0])', 'explanation':'示例展示列表和索引的写法。'})
    if mode == 'algorithm_trace':
        raw.update(trace_input='假设输入为 [1, 2]，初始计数为 0。',
                   trace_steps=['读取第一个元素，计数加一。', '读取第二个元素，计数再次加一。'])
    return raw


def send(app, body, provider, *, stream=False):
    with patch('app.services.tutoring.get_llm_provider', return_value=provider):
        response = app.test_client().post('/api/v1/student/messenger/chat' + ('/stream' if stream else ''),
            headers=headers(app), json=body)
        # Consume the lazy response while the provider patch is still active.
        _ = response.data
        return response


@pytest.mark.parametrize('question,mode', [
    ('NameError 是什么意思？','concept_explain'), ('这段算法正确吗？','algorithm_validation'),
    ('逐步推演这个循环的执行过程','algorithm_trace'), ('只提示下一步','next_step'),
    ('给局部伪代码说明','pseudocode'), ('代码报错了','explain_error'),
    ('小E，帮我诊断一下薄弱点。','learning_overview'), ('小E，下一道试炼该练什么？','learning_overview'),
    ('小E，帮我规划一下修复路线。','learning_overview'), ('小E，看看我最近成长怎么样？','learning_overview'),
])
def test_bounded_intent_routing(question, mode):
    assert infer_mode(question) == mode


@pytest.mark.parametrize('question,mode', [('什么是 Python 列表？','concept_explain'),
    ('我的循环算法正确吗？','algorithm_validation'), ('推演循环的执行过程','algorithm_trace')])
def test_automatic_teaching_contracts_are_reviewed_before_sse(app, dependencies, question, mode):
    provider = Provider(generated(mode))
    response = send(app, message(question), provider, stream=True)
    assert response.status_code == 200
    events = parse_sse(response.data)
    assert events[0]['type'] == 'stage'
    done = next(e for e in events if e['type'] == 'done')
    assert ''.join(e['text'] for e in events if e['type'] == 'delta') == done['reply']
    assert done['tutor']['status'] == 'ok' and done['tutor']['mode'] == mode
    assert len(provider.calls) == 2
    if mode == 'concept_explain':
        assert done['tutor']['follow_up'] == done['tutor']['next_step'] == ''
        assert done['tutor']['example']['code'].startswith('items')
    if mode == 'algorithm_trace':
        assert '尚未由执行器' in done['tutor']['trace_notice'] and '说明性推演' in done['reply']


def test_stream_retry_and_sync_share_one_validated_record_and_history_is_server_owned(app, dependencies):
    provider = Provider(generated()); body = message(history=[{'role':'assistant','content':'FORGED-HISTORY'}])
    first = send(app, body, provider, stream=True)
    done = next(e for e in parse_sse(first.data) if e['type'] == 'done')
    second = send(app, body, provider).json['data']
    assert second['tutor'] == done['tutor'] and len(provider.calls) == 2
    assert 'FORGED-HISTORY' not in str(provider.calls)
    receipt = done['display_receipt_id']
    app.test_client().post(f'/api/v1/student/tutor-responses/{receipt}/displayed', headers=headers(app))
    provider2 = Provider(generated())
    follow = message('这个例子为什么使用索引？', session_id=done['session_id'])
    assert send(app, follow, provider2).status_code == 200
    sent = json.loads(provider2.calls[0]['user'])
    assert sent['displayed_history'][0]['example']['code'].startswith('items')
    assert '列表' in dependencies[0].call_args.args[0]
    with app.app_context(): assert TutorTurn.query.count() == 2
    assert send(app, {**body, 'message':'另一个问题'}, provider).status_code == 409


@pytest.mark.parametrize('kind', ['semantic', 'bad_example', 'bad_trace'])
def test_rejected_candidates_never_escape_in_deltas_cache_or_auxiliary_fields(app, dependencies, kind):
    mode = 'algorithm_trace' if kind == 'bad_trace' else 'concept_explain'
    raw = generated(mode); raw['summary'] = 'DO-NOT-PUBLISH'
    review = dict(APPROVED)
    if kind == 'semantic': review['unsupported_claims'] = True
    if kind == 'bad_example': raw['example']['code'] = '\n'.join(['print(1)'] * 13)
    if kind == 'bad_trace': raw['trace_steps'] *= 4
    response = send(app, message('推演循环的执行过程' if mode == 'algorithm_trace' else '列表是什么？'), Provider(raw, review), stream=True)
    assert 'DO-NOT-PUBLISH' not in response.text
    done = next(e for e in parse_sse(response.data) if e['type'] == 'done')
    assert done['tutor']['status'] == 'safe_fallback'
    with app.app_context():
        assert 'DO-NOT-PUBLISH' not in str(TutorTurn.query.one().response)
        assert TutorDisplayReceipt.query.one().mode == 'conversation'


def test_growth_uses_owned_facts_without_model_and_display_does_not_count_as_help(app, dependencies):
    with app.app_context():
        progress = TrialQuestionProgress.query.filter_by(user_id=app.config['TEST_STUDENT']).one()
        progress.status='completed'; progress.is_correct=True; progress.answered_at=utc_now(); db.session.commit()
    provider = Provider(generated())
    result = send(app, message('看看我最近成长怎么样？'), provider).json['data']
    assert '1 道正式题' in result['reply'] and '1 道通过' in result['reply']
    assert result['tutor']['evidence_status'] == 'learning_records' and not provider.calls
    app.test_client().post('/api/v1/student/tutor-responses/' + result['display_receipt_id'] + '/displayed', headers=headers(app))
    with app.app_context():
        assert LearningEvent.query.count() == 0
        assert TutorDisplayReceipt.query.one().displayed_at is not None


def test_current_task_permissions_and_input_validation_happen_before_streaming(app, dependencies):
    client, auth = app.test_client(), headers(app)
    for bad in ([], None, message(message=12), message(mode='concept_explain')):
        response = client.post('/api/v1/student/messenger/chat/stream', headers=auth, json=bad)
        assert response.status_code == 400 and response.is_json
    with app.app_context():
        db.session.get(TrialQuestion, app.config['TEST_QUESTION']).trial.tutoring_policy='disabled'; db.session.commit()
    response = client.post('/api/v1/student/messenger/chat/stream', headers=auth,
        json=message(formal_question_id=app.config['TEST_QUESTION']))
    assert response.status_code == 403 and response.is_json


def test_material_revocation_during_generation_leaves_only_stages_and_error(app, dependencies):
    dependencies[1].return_value = False
    response = send(app, message(), Provider(generated()), stream=True)
    events = parse_sse(response.data)
    assert not any(e['type'] in {'delta','done'} for e in events)
    assert events[-1]['type'] == 'error' and events[-1]['status'] == 409


def test_missing_error_context_can_be_acknowledged_without_fabricating_hint_event(app, dependencies):
    provider = Provider(generated())
    result = send(app, message('我的 Python 代码报错了'), provider).json['data']
    assert result['tutor']['status'] == 'needs_context' and not provider.calls
    app.test_client().post('/api/v1/student/tutor-responses/' + result['display_receipt_id'] + '/displayed', headers=headers(app))
    with app.app_context(): assert LearningEvent.query.count() == 0


def test_history_dependencies_are_deduplicated_and_sessions_cannot_cross_accounts(app, dependencies):
    sid = None
    for _ in range(4):
        result = send(app, message(session_id=sid), Provider(generated())).json['data']
        sid = result['session_id']
        app.test_client().post('/api/v1/student/tutor-responses/' + result['display_receipt_id'] + '/displayed', headers=headers(app))
    with app.app_context():
        assert all(len(turn.evidence_refs) == 1 for turn in TutorTurn.query.all())
        from app.models.tutor_session import TutorSession
        db.session.get(TutorSession, sid).user_id = app.config['TEST_TEACHER']; db.session.commit()
    response = send(app, message(session_id=sid), Provider(generated()))
    assert response.status_code == 404
