"""Document/class ACLs apply before all recalls, after recall and at source release."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy.orm import Session
from app.models import db, User, Class, KnowledgeDocument, KnowledgeChunk
from app.services.knowledge.access_service import KnowledgeAccessService as Access
from app.services.knowledge.lexical_index import LexicalIndex
from app.services.knowledge.retrieval_service import RetrievalService
from app.services.knowledge.rag_service import KnowledgeRagService
from app.services.knowledge.schemas import LearnerContext, GraphContext, GraphNode
from test_learner_state import app


def materials(app):
    student = db.session.get(User, app.config['TEST_STUDENT'])
    teacher = db.session.get(User, app.config['TEST_TEACHER'])
    other_teacher = User.query.filter(User.username != teacher.username, User.role_id == teacher.role_id).first()
    if not other_teacher:
        other_teacher = User(username='acl-teacher', email='acl-teacher@example.com', password_hash='unused', role_id=teacher.role_id)
        db.session.add(other_teacher); db.session.flush()
    other_class = Class(name='Other class', teacher_id=other_teacher.id)
    db.session.add(other_class); db.session.flush()
    docs = {}
    cases = [
        ('public', 'public', True, None, 'READY', 'python-basics'),
        ('own', 'class', True, student.class_id, 'READY', 'python-basics'),
        ('private', 'private', False, None, 'READY', 'python-basics'),
        ('other', 'class', True, other_class.id, 'READY', 'python-basics'),
        ('draft', 'class', False, student.class_id, 'READY', 'python-basics'),
        ('failed', 'public', True, None, 'FAILED', 'python-basics'),
        ('course', 'public', True, None, 'READY', 'other-course'),
    ]
    for name, visibility, published, class_id, status, course_id in cases:
        doc = KnowledgeDocument(id=name, title=f'{name} 循环材料', uploaded_by=teacher.id if name != 'other' else other_teacher.id,
            visibility=visibility, published=published, class_id=class_id, status=status, course_id=course_id, version=2)
        db.session.add(doc)
        db.session.add(KnowledgeChunk(chunk_id=name, document_id=name, version=2, course_id=course_id,
            content=f'{name} ONLY 循环边界：range 不包含停止值。', primary_concept_id='loop-for', knowledge_type='concept_explanation'))
        docs[name] = doc
    for cid, kind, version in [('answer', 'solution', 2), ('note', 'teacher_note', 2), ('stale', 'example', 1)]:
        db.session.add(KnowledgeChunk(chunk_id=cid, document_id='public', version=version, course_id='python-basics',
            knowledge_type=kind, content=f'{cid} SECRET 循环边界。', primary_concept_id='loop-for'))
    db.session.commit()
    LexicalIndex.invalidate()
    return docs, other_class, other_teacher


def headers(user_id):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(user_id))}


class VectorIgnoringFilters:
    """A stale/malicious index is not the authority; SQL must reject its bad hits."""
    def __init__(self):
        self.embedding = SimpleNamespace(embed_query=lambda text: [1., 0.])
        self.store = SimpleNamespace(get=lambda ids: {})
        self.where = None

    def search_vector(self, vector, k, where):
        self.where = where
        return [SimpleNamespace(id=row.chunk_id, score=1., metadata={'document_id': 'forged'})
                for row in KnowledgeChunk.query.all()]


def retrieve(uid, *, documents=None):
    vector = VectorIgnoringFilters()
    graph = GraphContext(focus_ids=['loop-for'], nodes=[GraphNode('loop-for', '循环', 'concept', 'focus', 0, 1.)])
    with patch('app.services.knowledge.graph_service.GraphService.expand', return_value=graph):
        result = RetrievalService(vector).retrieve('循环 边界', LearnerContext(uid, role='admin'), document_ids=documents)
    return result, vector


def test_all_channels_filter_before_recall_and_reject_stale_index(app):
    with app.app_context():
        materials(app)
        result, vector = retrieve(app.config['TEST_STUDENT'])
        assert {c.chunk_id for c in result.candidates} == {'public', 'own'}
        assert set(vector.where['document_id']['$in']) == {'public', 'own'}
        assert set(vector.where['chunk_id']['$in']) == {'public', 'own'}
        assert all(c.version == 2 and c.document_id == c.chunk_id for c in result.candidates)
        assert all(c.to_source_dict()['url'].endswith('?version=2') for c in result.candidates)
        assert all('lexical' in c.retrieval_channels and 'graph' in c.retrieval_channels for c in result.candidates)


@pytest.mark.parametrize('documents', [[], ['other'], ['private'], ['failed'], ['course']])
def test_empty_or_forbidden_scope_never_falls_back_to_global(app, documents):
    with app.app_context():
        materials(app)
        result, vector = retrieve(app.config['TEST_STUDENT'], documents=documents)
        assert not result.candidates and vector.where is None


def test_source_routes_recheck_version_scope_and_type(app):
    with app.app_context():
        docs, _, _ = materials(app)
        auth = headers(app.config['TEST_STUDENT']); client = app.test_client()
        for cid in ('private', 'other', 'draft', 'failed', 'course', 'note', 'answer', 'stale'):
            assert client.get(f'/api/v1/rag/sources/{cid}?version=2', headers=auth).status_code == 404, cid
        assert client.get('/api/v1/rag/sources/own?version=1', headers=auth).status_code == 404
        assert client.get('/api/v1/rag/sources/own?version=bad', headers=auth).status_code == 400
        response = client.get('/api/v1/rag/sources/own?version=2', headers=auth)
        assert response.status_code == 200 and response.json['data']['version'] == 2
        docs['own'].published = False; db.session.commit()
        assert client.get('/api/v1/rag/sources/own?version=2', headers=auth).status_code == 404


def test_teacher_management_cannot_modify_other_documents_or_spoof_global_source(app):
    with app.app_context():
        docs, other_class, _ = materials(app)
        client = app.test_client(); auth = headers(app.config['TEST_TEACHER'])
        for method, suffix in [('get', ''), ('get', '/chunks'), ('patch', ''), ('post', '/index'), ('post', '/verify'), ('patch', '/access')]:
            assert getattr(client, method)('/api/v1/knowledge/documents/other' + suffix, headers=auth, json={}).status_code == 404
        body = {'visibility': 'class', 'class_id': other_class.id, 'published': True}
        assert client.patch('/api/v1/knowledge/documents/private/access', headers=auth, json=body).status_code == 400
        body['class_id'] = docs['own'].class_id
        response = client.patch('/api/v1/knowledge/documents/private/access', headers=auth, json=body)
        assert response.status_code == 200 and response.json['data']['published']
        body.update(visibility='public', class_id=None)
        assert client.patch('/api/v1/knowledge/documents/private/access', headers=auth, json=body).status_code == 400
        created = client.post('/api/v1/knowledge/documents', headers=auth, json={
            'title': '尝试伪造内置', 'text': '课程讲义。' * 10, 'source': 'builtin', 'auto_index': False,
            'visibility': 'public', 'published': True, 'meta': {'published': True}})
        assert created.status_code == 201
        doc = created.json['data']
        assert doc['source'] == 'manual' and doc['visibility'] == 'private' and not doc['published']


def test_role_and_class_are_derived_from_account_not_request(app):
    with app.app_context():
        docs, other_class, other_teacher = materials(app)
        uid = app.config['TEST_STUDENT']
        assert not Access.document(uid, 'private')
        assert Access.document(app.config['TEST_TEACHER'], 'private')
        assert not Access.document(other_teacher.id, 'private')
        student = db.session.get(User, uid); student.status = 'frozen'; db.session.commit()
        assert Access.chunks(uid).count() == 0


def test_teacher_as_user_cannot_be_another_class_or_an_admin(app):
    with app.app_context():
        _, other_class, _ = materials(app)
        client = app.test_client(); auth = headers(app.config['TEST_TEACHER'])
        student = db.session.get(User, app.config['TEST_STUDENT']); student.class_id = other_class.id; db.session.commit()
        for target in (student.id, app.config['TEST_TEACHER']):
            resp = client.post('/api/v1/rag/retrieve', headers=auth, json={'query': '循环边界', 'as_user_id': target})
            assert resp.status_code == 403


@pytest.mark.parametrize('change', ['revoke', 'version', 'class'])
def test_generation_rechecks_changes_in_independent_transaction(app, change):
    from app.services.knowledge.context_builder import BuiltContext
    from app.services.knowledge.schemas import RetrievedChunk, TeachingStrategy, QueryUnderstanding
    from app.services.knowledge.retrieval_service import RetrievalResult
    from app.services.knowledge.rag_service import RagPlan
    import time
    with app.app_context():
        _, other_class, _ = materials(app); uid = app.config['TEST_STUDENT']
        plan = RagPlan('循环', uid, 'student', 'chat', LearnerContext(uid),
            RetrievalResult(QueryUnderstanding('循环', '循环'), GraphContext()), TeachingStrategy(),
            [RetrievedChunk('own', 'own', '秘密材料', version=2)], BuiltContext('', '', '', '', source_index=[{'chunk_id': 'own', 'label': 'S1'}]),
            .9, 'HIGH', True, time.perf_counter())
        # End the read transaction, retaining a stale ORM identity map intentionally.
        db.session.commit(); stale_user = db.session.get(User, uid); _ = stale_user.class_id
        db.session.commit()
        with Session(db.engine) as session:
            if change == 'revoke': session.get(KnowledgeDocument, 'own').published = False
            elif change == 'version': session.get(KnowledgeDocument, 'own').version = 3
            else: session.get(User, uid).class_id = other_class.id
            session.commit()
        assert not Access.plan_is_current(plan)
        answer = KnowledgeRagService().finalize(plan, answer_text='秘密材料的答案', generation_mode='llm')
        assert '秘密材料' not in answer.answer
        assert not answer.sources and not answer.knowledge_grounded
        assert plan.extra['evidence_status'] == 'source_changed'


def test_migration_private_by_default_only_system_builtin_public(app):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text
    path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261016_0020_knowledge_access.py'
    spec = importlib.util.spec_from_file_location('access_migration', path)
    migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
    with app.app_context():
        docs, _, _ = materials(app)
        docs['public'].source = 'builtin'; docs['public'].uploaded_by = None
        docs['private'].source = 'builtin'
        db.session.commit(); db.session.remove()
        with db.engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            migration.downgrade(); migration.upgrade(); migration.upgrade()
            values = {r.id: (r.visibility, bool(r.published)) for r in conn.execute(text('SELECT id, visibility, published FROM knowledge_documents'))}
            assert values['public'] == ('public', True)
            assert all(value == ('private', False) for key, value in values.items() if key != 'public')


def test_stream_never_releases_partial_provider_or_prevalidation_text(app):
    from app.services.messenger_tutoring import MessengerTutoring
    from test_tutoring_modes import Provider, candidate, EVIDENCE
    app.config['TUTOR_MODELS_ENABLED'] = True
    provider = Provider({**candidate(), 'example': None})
    with app.app_context(), \
         patch('app.services.tutoring.get_llm_provider', return_value=provider), \
         patch('app.services.tutoring.KnowledgeService.tutor_evidence', return_value=EVIDENCE), \
         patch('app.services.tutoring.KnowledgeService.tutor_sources_current', return_value=True):
        payload = MessengerTutoring.prepare(app.config['TEST_STUDENT'], {'message':'Python 循环是什么？'})
        iterator = MessengerTutoring.stream(app.config['TEST_STUDENT'], payload)
        assert next(iterator)['type'] == 'stage' and not provider.calls
        events = list(iterator)
        assert len(provider.calls) == 2
        assert ''.join(e['text'] for e in events if e['type'] == 'delta') == next(e['reply'] for e in events if e['type'] == 'done')


def test_validation_failure_does_not_fall_back_to_unchecked_raw_text(app):
    from app.services.messenger_tutoring import MessengerTutoring
    from test_tutoring_modes import Provider, candidate, EVIDENCE
    app.config['TUTOR_MODELS_ENABLED'] = True
    provider = Provider({**candidate(), 'summary':'秘密课程原文', 'example':None})
    with app.app_context(), \
         patch('app.services.tutoring.get_llm_provider', return_value=provider), \
         patch('app.services.tutoring.KnowledgeService.tutor_evidence', return_value=EVIDENCE), \
         patch('app.services.tutoring.KnowledgeService.tutor_sources_current', return_value=True), \
         patch('app.services.tutoring.semantic_review_ok', side_effect=RuntimeError('unavailable')):
        payload = MessengerTutoring.prepare(app.config['TEST_STUDENT'], {'message':'Python 循环是什么？'})
        events = list(MessengerTutoring.stream(app.config['TEST_STUDENT'], payload))
        assert '秘密课程原文' not in str(events)
        assert next(e['tutor']['status'] for e in events if e['type'] == 'done') == 'safe_fallback'
