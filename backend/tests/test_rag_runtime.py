"""Real SQLite/MySQL admission transactions; provider behavior is synthetic."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
from pathlib import Path
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import update, text
from sqlalchemy.orm import Session
from flask_jwt_extended import create_access_token

from test_learner_state import app
from test_tutor_context import headers
from app.models import db, User, KnowledgeChunk, KnowledgeDocument
from app.models.rag_runtime import RagRequest as Request, RagRequestAttempt as Attempt
from app.services import rag_runtime as runtime
from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.knowledge.schemas import RagAnswer, RetrievedChunk
from app.utils.time import utc_now


def fake_plan(*args, **kwargs):
    return SimpleNamespace(chunks=[], retrieval=SimpleNamespace(candidates=[]), debug=kwargs.get('debug', False),
                           learner=SimpleNamespace(state_version=None), blocked_reason=None)


def fake_answer(plan=None, **kwargs):
    return RagAnswer(answer=kwargs.get('answer_text', '课程回答'), concepts=[], sources=[], confidence=.5,
        confidence_level='MEDIUM', knowledge_grounded=True, teaching_strategy={}, recommended_next=[],
        generation_mode=kwargs.get('generation_mode', 'llm'), debug={'candidates': []} if plan and plan.debug else None)


@contextmanager
def pipeline(plan=None, generate=None):
    with patch.object(runtime.KnowledgeRagService, 'prepare', side_effect=plan or fake_plan), \
         patch.object(runtime.KnowledgeRagService, 'generate', side_effect=generate or (lambda *a, **k: ('课程回答', 'llm', {}))) as calls, \
         patch.object(runtime.KnowledgeRagService, 'finalize', side_effect=fake_answer):
        yield calls


def ask(app, rid=None, **kwargs):
    with app.app_context():
        return KnowledgeService.answer('循环边界', user_id=app.config['TEST_TEACHER'], role='teacher', request_id=rid or str(uuid.uuid4()), **kwargs)


def test_rag_runtime_replay_conflict_quota_and_owner(app):
    app.config['RAG_DAILY_REQUEST_LIMIT'] = 1
    rid = str(uuid.uuid4())
    with pipeline() as calls:
        first = ask(app, rid)
        assert ask(app, rid).to_dict() == first.to_dict() and calls.call_count == 1
        with pytest.raises(runtime.RagRuntimeError, match='其他内容'): ask(app, rid, scene='trial')
        with pytest.raises(runtime.RagRuntimeError) as exc: ask(app)
        assert exc.value.status == 429
        with app.app_context():
            result = runtime.restore(app.config['TEST_TEACHER'], rid)
            assert result['status'] == 'complete' and result['answer']['request_id'] == rid
            assert 'debug' not in result['answer'] and 'evidence_refs' not in result['answer']
            assert runtime.usage(app.config['TEST_TEACHER'])['requests_used'] == 1
            teacher = db.session.get(User, app.config['TEST_TEACHER'])
            other = User(username='rag-other', email='rag-other@example.test', role_id=teacher.role_id, password_hash='test')
            db.session.add(other); db.session.commit(); uid = other.id; db.session.rollback()
            with pytest.raises(runtime.RagRuntimeError) as exc: runtime.restore(uid, rid)
            assert exc.value.status == 404
            with pytest.raises(runtime.RagRuntimeError) as exc: runtime.claim(uid, 'teacher', rid, 'x')
            assert exc.value.status == 404


def test_rag_runtime_parallel_duplicate_and_capacity(app):
    rid = str(uuid.uuid4())
    def reserve(index):
        with app.app_context():
            try: return runtime.claim(app.config['TEST_TEACHER'], 'teacher', rid, 'same')
            except runtime.RagRuntimeError as exc: return exc.reason
    with ThreadPoolExecutor(5) as pool: results = list(pool.map(reserve, range(5)))
    assert len([r for r in results if isinstance(r, dict)]) == 1
    assert results.count('request_in_progress') == 4
    def distinct(index):
        with app.app_context():
            try: return runtime.claim(app.config['TEST_TEACHER'], 'teacher', str(uuid.uuid4()), 'body')
            except runtime.RagRuntimeError as exc: return exc.reason
    with ThreadPoolExecutor(5) as pool: results = list(pool.map(distinct, range(5)))
    assert len([r for r in results if isinstance(r, dict)]) == 1
    assert results.count('capacity_reached') == 4
    with app.app_context(): assert Attempt.query.count() == 2


def test_rag_runtime_global_capacity_across_users(app):
    app.config['RAG_GLOBAL_CONCURRENCY'] = 1
    with app.app_context():
        teacher = db.session.get(User, app.config['TEST_TEACHER'])
        second = User(username='rag-second', email='rag-second@example.test', role_id=teacher.role_id, password_hash='test')
        db.session.add(second); db.session.commit(); uid = second.id
        runtime.claim(app.config['TEST_TEACHER'], 'teacher', str(uuid.uuid4()), 'x')
        with pytest.raises(runtime.RagRuntimeError) as exc: runtime.claim(uid, 'teacher', str(uuid.uuid4()), 'x')
        assert exc.value.reason == 'capacity_reached'


def test_rag_runtime_failure_retry_limit_and_daily_attempts(app):
    rid = str(uuid.uuid4())
    with pipeline(generate=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('synthetic failure'))) as calls:
        for _ in range(3):
            with pytest.raises(RuntimeError, match='synthetic'): ask(app, rid)
        with pytest.raises(runtime.RagRuntimeError) as exc: ask(app, rid)
        assert exc.value.reason == 'attempt_limit' and calls.call_count == 3
    with app.app_context():
        assert runtime.restore(app.config['TEST_TEACHER'], rid)['status'] == 'failed'
        assert runtime.usage(app.config['TEST_TEACHER'])['requests_used'] == 3
        assert runtime.usage(app.config['TEST_TEACHER'])['active_requests'] == 0
        assert {r.error_code for r in Request.query.all()} == {'generation_failed'}


def test_rag_runtime_expired_worker_cannot_publish_or_damage_successor(app):
    rid = str(uuid.uuid4())
    with app.app_context():
        uid = app.config['TEST_TEACHER']; old = runtime.claim(uid, 'teacher', rid, 'x')
        past = utc_now() - timedelta(seconds=1)
        db.session.execute(update(Request).values(lease_until=past)); db.session.execute(update(Attempt).values(lease_until=past)); db.session.commit()
        assert runtime.restore(uid, rid)['status'] == 'expired'
        new = runtime.claim(uid, 'teacher', rid, 'x')
        with pytest.raises(runtime.RagRuntimeError): runtime.finish(old, fake_answer(), [])
        answer = fake_answer(); answer.request_id = rid
        runtime.finish(new, answer, [])
        runtime.fail(old, 'late_failure')
        assert runtime.restore(uid, rid)['status'] == 'complete'
        db.session.rollback()
        assert {a.status for a in Attempt.query.all()} == {'complete', 'failed'}


def material_plan(app, debug=False):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first() or User.query.filter_by(username='admin001').one()
        doc = KnowledgeDocument(id='rag-doc', title='循环边界', course_id='python-basics', status='READY',
            version=1, visibility='public', published=True, uploaded_by=admin.id)
        db.session.add(doc); db.session.flush()
        chunk = KnowledgeChunk(chunk_id='rag-chunk', document_id=doc.id, title='边界', content='循环边界课程证据',
            course_id='python-basics', version=1, status='active')
        db.session.add(chunk); db.session.commit()
    p = fake_plan(debug=debug)
    source = RetrievedChunk('rag-chunk', 'rag-doc', '循环边界课程证据', version=1)
    if debug: p.retrieval.candidates = [source]  # Not selected, but exposed in admin diagnostics.
    else: p.chunks = [source]
    return p


@pytest.mark.parametrize('change', ['content', 'version', 'visibility', 'status'])
def test_rag_runtime_replay_revalidates_evidence(app, change):
    plan = material_plan(app); rid = str(uuid.uuid4())
    with pipeline(plan=lambda *a, **k: plan) as calls:
        ask(app, rid)
        with app.app_context():
            if change == 'content': db.session.execute(update(KnowledgeChunk).values(content='changed same version'))
            else: db.session.execute(update(KnowledgeDocument).values(**{change: {'version': 2, 'visibility': 'private', 'status': 'PENDING'}[change]}))
            db.session.commit()
            with pytest.raises(runtime.RagRuntimeError) as exc: runtime.restore(app.config['TEST_TEACHER'], rid)
            assert exc.value.reason == 'sources_changed'
        with pytest.raises(runtime.RagRuntimeError): ask(app, rid)
        assert calls.call_count == 1


def test_rag_runtime_withdrawal_during_generation_prevents_publication(app):
    plan = material_plan(app); rid = str(uuid.uuid4())
    def generate(*a, **k):
        with Session(db.engine) as session:
            session.execute(update(KnowledgeDocument).values(visibility='private')); session.commit()
        return 'must never publish', 'llm', {}
    with pipeline(plan=lambda *a, **k: plan, generate=generate):
        with pytest.raises(runtime.RagRuntimeError) as exc: ask(app, rid)
        assert exc.value.reason == 'sources_changed'
    with app.app_context():
        row = db.session.get(Request, rid)
        assert row.status == 'failed' and row.response is None


def test_rag_runtime_debug_candidates_and_role_changes(app):
    plan = material_plan(app, debug=True); rid = str(uuid.uuid4())
    with app.app_context():
        admin = User.query.filter_by(username='admin').first() or User.query.filter_by(username='admin001').one()
        uid = admin.id; db.session.rollback()
        with pipeline(plan=lambda *a, **k: plan):
            KnowledgeService.answer('循环', user_id=uid, role='admin', debug=True, request_id=rid)
        assert 'debug' in runtime.restore(uid, rid)['answer']
        db.session.execute(update(KnowledgeChunk).values(status='inactive')); db.session.commit()
        with pytest.raises(runtime.RagRuntimeError) as exc: runtime.restore(uid, rid)
        assert exc.value.reason == 'sources_changed'
        db.session.execute(update(KnowledgeChunk).values(status='active'))
        teacher = db.session.get(User, app.config['TEST_TEACHER'])
        db.session.execute(update(User).where(User.id == uid).values(role_id=teacher.role_id)); db.session.commit()
        with pytest.raises(runtime.RagRuntimeError) as exc: runtime.restore(uid, rid)
        assert exc.value.reason == 'access_changed'


def test_rag_runtime_api_ownership_validation_and_processing(app):
    client = app.test_client(); rid = str(uuid.uuid4()); route = '/api/v1/rag'
    assert client.get(route + '/usage').status_code == 401
    assert client.get(route + '/usage', headers=headers(app)).status_code == 403
    teacher = headers(app, True)
    for body in [[], {'query': '循环', 'scene': []}, {'query': '循环', 'request_id': 'bad'}, {'query': '循环', 'context': {'concept_hint': []}}, {'query': '循环', 'context': {'concept_ids': [1]}}]:
        assert client.post(route + '/query', json=body, headers=teacher).status_code == 400
    with app.app_context(): runtime.claim(app.config['TEST_TEACHER'], 'teacher', rid, 'x')
    result = client.get(route + '/requests/' + rid, headers=teacher)
    assert result.status_code == 200 and result.json['data']['status'] == 'processing' and result.json['data']['answer'] is None
    with pipeline():
        result = client.post(route + '/query', json={'query': '循环', 'request_id': str(uuid.uuid4())}, headers=teacher)
        assert result.status_code == 200 and result.json['data']['request_id']
        assert 'debug' not in result.json['data']


def test_rag_runtime_migration_preserves_users_and_repeats(app):
    with app.app_context():
        users = User.query.count(); db.session.remove()
        with db.engine.begin() as conn:
            conn.execute(text('DROP TABLE rag_request_attempts')); conn.execute(text('DROP TABLE rag_requests'))
            path = Path(__file__).parents[1] / 'migrations/versions/20261018_0032_rag_runtime.py'
            spec = importlib.util.spec_from_file_location('rag_migration', path); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(conn)): module.upgrade(); module.upgrade()
        assert User.query.count() == users and Request.query.count() == 0
    with pipeline(): assert ask(app).request_id
