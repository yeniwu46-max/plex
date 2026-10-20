"""HTTP tests against isolated SQLite; no real accounts or model calls."""
from uuid import uuid4

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from app.models import Class, Role, Trial, TrialQuestion, TutorGuidanceTurn, User, db
from app.routes.agent_service import agent_bp


@pytest.fixture()
def env():
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
                      SQLALCHEMY_TRACK_MODIFICATIONS=False, JWT_SECRET_KEY='test-key-only-32-characters-long!!')
    db.init_app(app)
    JWTManager(app)
    app.register_blueprint(agent_bp)
    with app.app_context():
        db.create_all()
        role = Role(name='student')
        db.session.add(role)
        db.session.flush()
        users = [User(username=f'guidance-{i}', email=f'g{i}@example.invalid',
                      password_hash='not-a-login-password', role_id=role.id) for i in range(2)]
        db.session.add_all(users)
        db.session.commit()
        tokens = [create_access_token(identity=str(user.id)) for user in users]
        yield app.test_client(), tokens, users
        db.session.remove()
        db.drop_all()


def call(env, action, body, user=0):
    return env[0].post('/api/v1/agents/tutor-guidance/' + action, json=body,
                       headers={'Authorization': 'Bearer ' + env[1][user]})


def payload(**overrides):
    return {'requestId': str(uuid4()), 'exerciseId': 'loop-sum', 'questionPrompt': '计算所有元素的和',
            'code': 'for i in range(2):\n    print(i)', 'mode': 'auto', **overrides}


def ask(env, **overrides):
    response = call(env, 'ask', payload(**overrides))
    assert response.status_code == 200, response.json
    return response.json['data']


def confirm(env, result):
    response = call(env, 'acknowledge', {'requestId': result['requestId']})
    assert response.status_code == 200
    assert response.json['data']['displayed']


@pytest.mark.parametrize(('changes', 'mode'), [
    ({'stderr': "NameError: name 'x' is not defined"}, 'error_explanation'),
    ({'thought': '先累加，再输出结果'}, 'thought_check'),
    ({}, 'next_step'),
])
def test_recommendation_has_reason(env, changes, mode):
    response = call(env, 'plan', payload(**changes))
    assert response.status_code == 200
    recommendation = response.json['data']['recommendation']
    assert recommendation['mode'] == mode
    assert recommendation['reason']
    assert TutorGuidanceTurn.query.count() == 0


def test_explicit_mode_overrides_recommendation(env):
    result = ask(env, mode='next_step', stderr='IndexError: out of range')
    assert result['mode'] == 'next_step'
    assert result['recommendation']['mode'] == 'error_explanation'


def test_confirmed_progress_and_bounded_local_scaffold(env):
    first = ask(env)
    assert first['stage'] == 1
    confirm(env, first)
    second = ask(env, previousRequestId=first['requestId'], furtherHelp=True)
    assert second['stage'] == 2
    assert first['response'] != second['response']
    confirm(env, second)
    plan = call(env, 'plan', payload(previousRequestId=second['requestId'])).json['data']
    assert plan['recommendation']['mode'] == 'local_pseudocode'
    third = ask(env, previousRequestId=second['requestId'], furtherHelp=True)
    assert third['stage'] == 3
    assert not third['canDeepen']
    assert '由你补充' in third['response'] or '你自己的' in third['response']
    confirm(env, third)
    fourth = ask(env, previousRequestId=third['requestId'], furtherHelp=True)
    assert fourth['stage'] == 3


def test_no_advance_without_confirmation_or_explicit_help(env):
    first = ask(env)
    unconfirmed = ask(env, previousRequestId=first['requestId'], furtherHelp=True)
    assert unconfirmed['stage'] == 1
    confirm(env, first)
    regular = ask(env, previousRequestId=first['requestId'])
    assert regular['stage'] == 1
    skipped = ask(env, hintLevel=4, stage=3, furtherHelp=True)
    assert skipped['stage'] == 1


def test_retry_is_identical_and_input_reuse_is_rejected(env):
    body = payload()
    first = call(env, 'ask', body).json['data']
    confirm(env, first)
    assert call(env, 'ask', body).json['data'] == first
    assert TutorGuidanceTurn.query.count() == 1
    assert call(env, 'ask', {**body, 'code': 'print(1)'}).status_code == 400
    confirm(env, first)
    assert TutorGuidanceTurn.query.count() == 1


@pytest.mark.parametrize('changes', [
    {'code': 'for j in range(3):\n    print(j)'},
    {'exerciseId': 'other-question'},
    {'questionPrompt': '修订后的题目'},
    {'userQuestion': '我想检查输出格式'},
])
def test_changed_code_question_revision_or_focus_resets(env, changes):
    first = ask(env)
    confirm(env, first)
    second = ask(env, previousRequestId=first['requestId'], furtherHelp=True, **changes)
    assert second['stage'] == 1


def test_other_users_turn_cannot_confirm_or_deepen(env):
    first = ask(env)
    confirm(env, first)
    assert call(env, 'acknowledge', {'requestId': first['requestId']}, user=1).status_code == 400
    response = call(env, 'ask', payload(previousRequestId=first['requestId'], furtherHelp=True), user=1)
    assert response.json['data']['stage'] == 1


@pytest.mark.parametrize('mode', ['error_explanation', 'thought_check'])
def test_missing_context_does_not_count_as_displayed_hint(env, mode):
    result = ask(env, mode=mode)
    assert result['needsContext']
    ack = call(env, 'acknowledge', {'requestId': result['requestId']})
    assert not ack.json['data']['displayed']


def test_local_pseudocode_does_not_jump_stages(env):
    result = ask(env, mode='local_pseudocode')
    assert result['stage'] == 1
    assert 'print(i)' not in result['response']


def test_deepen_keeps_explicit_student_concern(env):
    first = ask(env, userQuestion='我想检查输出格式')
    confirm(env, first)
    second = ask(env, previousRequestId=first['requestId'], furtherHelp=True)
    assert second['stage'] == 2
    assert '逐字符比较' in second['response']


def test_durable_after_session_removal(env):
    body = payload()
    first = call(env, 'ask', body).json['data']
    confirm(env, first)
    db.session.remove()
    assert call(env, 'ask', body).json['data'] == first
    second = ask(env, previousRequestId=first['requestId'], furtherHelp=True)
    assert second['stage'] == 2


def test_auth_and_validation(env):
    assert env[0].post('/api/v1/agents/tutor-guidance/ask', json=payload()).status_code == 401
    for body in [[], {}, payload(requestId='invalid'), payload(mode='give_answer'),
                 payload(furtherHelp='true'), payload(code='x' * 16001)]:
        assert call(env, 'ask', body).status_code == 400


def test_bound_trial_permissions_and_replay_recheck(env):
    user = env[2][0]
    classroom = Class(name='isolated class', teacher_id=user.id)
    db.session.add(classroom)
    db.session.flush()
    user.class_id = classroom.id
    trial = Trial(class_id=classroom.id, teacher_id=user.id, title='trial', status='running', trial_type='solo')
    db.session.add(trial)
    db.session.flush()
    question = TrialQuestion(trial_id=trial.id, stem='server question', options=[], question_type='coding')
    db.session.add(question)
    db.session.commit()
    body = payload(trialQuestionId=question.id)
    assert call(env, 'ask', body, user=1).status_code == 400
    assert call(env, 'ask', body).status_code == 200
    trial.status = 'draft'
    db.session.commit()
    assert call(env, 'ask', body).status_code == 400
    trial.status, trial.trial_type = 'running', 'group'
    db.session.commit()
    assert call(env, 'ask', payload(trialQuestionId=question.id)).status_code == 400


@pytest.mark.parametrize(('candidate', 'review', 'backend'), [
    ('请记录最后一次循环时的变量值，并核对是否覆盖目标范围。', {'approved': True}, 'llm_reviewed'),
    ('完整答案', {'approved': False}, 'pedagogical_rules'),
    ('完整答案', {'approved': 'true'}, 'pedagogical_rules'),
    ('完整答案', None, 'pedagogical_rules'),
    ('```python\nprint(42)\n```', {'approved': True}, 'pedagogical_rules'),
])
def test_model_draft_requires_review_before_display(env, monkeypatch, candidate, review, backend):
    from app.services import tutor_guidance as service
    monkeypatch.setattr(service, 'llm_provider', lambda: ('test', 'test', 'test'))
    monkeypatch.setattr(service, 'chat_text', lambda **kwargs: candidate)
    monkeypatch.setattr(service, 'chat_json', lambda **kwargs: review)
    result = ask(env)
    assert result['backend'] == backend
    if backend == 'pedagogical_rules':
        assert result['response'] != candidate


def test_duplicate_does_not_call_model_twice_and_repetition_falls_back(env, monkeypatch):
    from app.services import tutor_guidance as service
    calls = []
    monkeypatch.setattr(service, 'llm_provider', lambda: ('test', 'test', 'test'))
    monkeypatch.setattr(service, 'chat_text', lambda **kwargs: calls.append(kwargs) or '观察最后一次循环是否覆盖目标。')
    monkeypatch.setattr(service, 'chat_json', lambda **kwargs: {'approved': True})
    body = payload()
    first = call(env, 'ask', body).json['data']
    assert call(env, 'ask', body).json['data'] == first
    assert len(calls) == 1
    confirm(env, first)
    second = ask(env, previousRequestId=first['requestId'], furtherHelp=True)
    assert second['backend'] == 'pedagogical_rules'
    assert second['response'] != first['response']


def test_inflight_request_and_expired_lease_recovery(env, monkeypatch):
    from datetime import timedelta
    from app.services import tutor_guidance as service
    from app.utils.time import utc_now
    body = payload()
    # A process interruption after reservation leaves a recoverable pending row.
    monkeypatch.setattr(service, '_model_hint', lambda *args: (_ for _ in ()).throw(RuntimeError('interrupted')))
    with pytest.raises(RuntimeError):
        call(env, 'ask', body)
    row = TutorGuidanceTurn.query.one()
    assert row.result is None
    assert call(env, 'ask', body).status_code == 400
    row.lease_expires_at = utc_now() - timedelta(seconds=1)
    db.session.commit()
    monkeypatch.setattr(service, '_model_hint', lambda *args: (args[-1], 'pedagogical_rules'))
    recovered = call(env, 'ask', body)
    assert recovered.status_code == 200, recovered.json
    assert recovered.json['data']['stage'] == 1
    assert TutorGuidanceTurn.query.count() == 1


def test_migration_upgrade_downgrade_preserves_existing_tables(env):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    path = Path(__file__).parents[1] / 'migrations/versions/20261020_0016_tutor_guidance.py'
    spec = importlib.util.spec_from_file_location('guidance_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    TutorGuidanceTurn.__table__.drop(db.engine)
    with db.engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert 'tutor_guidance_turns' in inspect(connection).get_table_names()
        migration.downgrade()
        assert 'tutor_guidance_turns' not in inspect(connection).get_table_names()
        assert 'users' in inspect(connection).get_table_names()
        migration.upgrade()
    assert ask(env)['stage'] == 1


@pytest.fixture()
def course(env, monkeypatch):
    from app.models import KnowledgeDocument, KnowledgeChunk
    from app.services import tutor_guidance as service
    from app.services.knowledge import KnowledgeService
    document = KnowledgeDocument(title='循环课程', source='builtin', status='READY',
                                 teacher_verified=True, version=1, course_id='python-basics')
    db.session.add(document)
    db.session.flush()
    chunk = KnowledgeChunk(document_id=document.id, content='range 的 stop 不包含在生成的序列中。',
                           title='for 与 range', status='active', version=1, teacher_verified=True,
                           knowledge_type='concept_explanation', course_id='python-basics')
    db.session.add(chunk)
    db.session.commit()
    retrieval_calls = []
    def retrieve(*args, **kwargs):
        retrieval_calls.append((args, kwargs))
        return {'knowledge_grounded': True, 'reranked': [{'chunk_id': chunk.chunk_id}]}
    monkeypatch.setattr(KnowledgeService, 'retrieve', retrieve)
    monkeypatch.setattr(service, 'llm_provider', lambda: ('test', 'test', 'test'))
    monkeypatch.setattr(service, 'chat_text', lambda **kwargs: '观察 range 的结束边界，检查最后一次访问。[S1]')
    monkeypatch.setattr(service, 'chat_json', lambda **kwargs: {'approved': True})
    return document, chunk, retrieval_calls


@pytest.mark.parametrize('mode', ['next_step', 'thought_check', 'error_explanation', 'local_pseudocode'])
def test_course_evidence_is_mode_scoped_and_student_safe(env, course, mode):
    _, _, calls = course
    result = ask(env, mode=mode, thought='先累加再输出', stderr='IndexError: out of range')
    assert result['evidenceStatus'] == 'grounded'
    assert result['citations'][0]['label'] == 'S1'
    assert '_evidence' not in result
    assert 'contentHash' not in str(result)
    assert 'solution' not in calls[0][1]['knowledge_types']
    assert 'example' not in calls[0][1]['knowledge_types']
    detail = call(env, 'source', {'requestId': result['requestId'], 'label': 'S1'})
    assert detail.status_code == 200
    assert 'stop' in detail.json['data']['excerpt']
    assert call(env, 'source', {'requestId': result['requestId'], 'label': 'S99'}).status_code == 400
    assert call(env, 'source', {'requestId': result['requestId'], 'label': 'S1'}, user=1).status_code == 400


@pytest.mark.parametrize('mutation', ['withdraw', 'version', 'content', 'unverify', 'stale', 'private'])
def test_changed_material_invalidates_replay_read_source_ack_and_parent(env, course, mutation):
    document, chunk, _ = course
    body = payload()
    response = call(env, 'ask', body)
    result = response.json['data']
    confirm(env, result)
    if mutation == 'withdraw': document.status = 'FAILED'
    elif mutation == 'version': document.version = 2
    elif mutation == 'content': chunk.content = 'Updated course content'
    elif mutation == 'unverify': document.teacher_verified = False
    elif mutation == 'stale': chunk.status = 'stale'
    else: document.source = 'upload'
    db.session.commit()
    assert call(env, 'ask', body).status_code == 400
    for action in ['read', 'source', 'acknowledge']:
        assert call(env, action, {'requestId': result['requestId'], 'label': 'S1'}).status_code == 400
    assert call(env, 'ask', payload(previousRequestId=result['requestId'], furtherHelp=True)).status_code == 400


@pytest.mark.parametrize('candidate', ['没有引用的课程结论', '引用不存在的材料[S99]'])
def test_missing_or_invented_citation_uses_general_fallback(env, course, monkeypatch, candidate):
    from app.services import tutor_guidance as service
    monkeypatch.setattr(service, 'chat_text', lambda **kwargs: candidate)
    result = ask(env)
    assert result['backend'] == 'pedagogical_rules'
    assert result['evidenceStatus'] == 'general'
    assert result['citations'] == []
    assert result['response'] != candidate


def test_material_revoked_during_generation_never_enters_response(env, course, monkeypatch):
    from app.services import tutor_guidance as service
    document, _, _ = course
    def review(**kwargs):
        document.status = 'FAILED'
        db.session.commit()
        return {'approved': True}
    monkeypatch.setattr(service, 'chat_json', review)
    response = call(env, 'ask', payload())
    assert response.status_code == 400
    assert 'range' not in str(response.json)
    assert TutorGuidanceTurn.query.one().result is None


def test_uploaded_private_document_not_used_as_course_evidence(env, course):
    document, _, _ = course
    document.source = 'upload'
    db.session.commit()
    result = ask(env)
    assert result['evidenceStatus'] == 'insufficient'
    assert not result['citations']


def test_uncited_material_also_revalidated(env, course, monkeypatch):
    from app.models import KnowledgeDocument, KnowledgeChunk
    from app.services.knowledge import KnowledgeService
    document, chunk, _ = course
    extra = KnowledgeDocument(title='其他课程片段', source='builtin', status='READY', teacher_verified=True)
    db.session.add(extra)
    db.session.flush()
    extra_chunk = KnowledgeChunk(document_id=extra.id, content='循环的相关概念', status='active', teacher_verified=True)
    db.session.add(extra_chunk)
    db.session.commit()
    monkeypatch.setattr(KnowledgeService, 'retrieve', lambda *args, **kwargs: {
        'knowledge_grounded': True, 'reranked': [{'chunk_id': chunk.chunk_id}, {'chunk_id': extra_chunk.chunk_id}],
    })
    result = ask(env)
    assert len(result['citations']) == 1
    extra.status = 'FAILED'
    db.session.commit()
    assert call(env, 'read', {'requestId': result['requestId']}).status_code == 400


def test_low_confidence_material_not_passed_to_model(env, course, monkeypatch):
    from app.services.knowledge import KnowledgeService
    monkeypatch.setattr(KnowledgeService, 'retrieve', lambda *args, **kwargs: {
        'knowledge_grounded': False, 'reranked': [{'chunk_id': course[1].chunk_id}],
    })
    result = ask(env)
    assert result['evidenceStatus'] == 'insufficient'
    assert result['citations'] == []


def test_retrieval_outage_returns_labeled_general_help(env, course, monkeypatch):
    from app.services.knowledge import KnowledgeService
    def fail(*args, **kwargs):
        raise RuntimeError('retrieval unavailable')
    monkeypatch.setattr(KnowledgeService, 'retrieve', fail)
    result = ask(env)
    assert result['evidenceStatus'] == 'unavailable'
    assert result['citations'] == []
