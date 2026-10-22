"""Resource generation grounds in owner-authorized, versioned course evidence."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import importlib.util
from unittest.mock import patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from test_learner_state import app, append
from test_resource_learning_context import queued, set_profile
from test_knowledge_access import materials as acl_materials, headers, VectorIgnoringFilters
from app.models import db, KnowledgeDocument, KnowledgeChunk, ResourceGenerationTask, PersonalizedLearningResource, User
from app.services.personalized_resource import PersonalizedResourceService as Resources
from app.services.resource_course_evidence import ResourceCourseEvidence as Evidence
from app.services.resource_learning_context import ResourceLearningContext as Context
from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.knowledge.learner_context_service import LearnerContextService
from app.services.knowledge.retrieval_service import RetrievalService
from app.services.knowledge.schemas import LearnerContext, GraphContext, GraphNode
from app.services.learner_state import LearnerStateService as State


def materials(app):
    result = acl_materials(app)
    # Realistic topic-bearing text; retain the malicious index's forbidden hits.
    for row in KnowledgeChunk.query.all():
        row.content += ' for 循环结构 循环边界 概念 示例 常见错误。'
        row.concept_ids = ['loop-for']
    db.session.commit()
    from app.services.knowledge.lexical_index import LexicalIndex
    LexicalIndex.invalidate()
    return result


@contextmanager
def indexed():
    graph = GraphContext(focus_ids=['loop-for'], nodes=[GraphNode('loop-for', '循环', 'concept', 'focus', 0, 1.)])
    with patch('app.services.knowledge.rag_service.RetrievalService', return_value=RetrievalService(VectorIgnoringFilters())), \
         patch('app.services.knowledge.graph_service.GraphService.expand', return_value=graph):
        yield


def run(app):
    task = queued(app)
    db.session.rollback()
    with indexed():
        Resources.run_task(app, task['task_id'])
    db.session.rollback()
    result = Resources.get_task(app.config['TEST_STUDENT'], task['task_id'])
    assert result['status'] == 'completed', result['error']
    return result


def test_frozen_resource_learner_never_reads_live_mode_profile_or_scores(app):
    app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
    with app.app_context():
        set_profile(app)
        append(app); db.session.commit(); State.drain()
        frozen = Context.capture(app.config['TEST_STUDENT'], 'loop-for')
        app.config['LEARNER_STATE_READ_MODE'] = 'shadow'
        set_profile(app, '有工作经验', 4)
        with patch.object(LearnerContextService, 'build', side_effect=AssertionError('live context read')):
            ctx = LearnerContextService.from_resource_snapshot(frozen)
            with indexed():
                plan = KnowledgeService.prepare('循环边界', user_id=ctx.user_id, learner_context=ctx)
        assert plan.learner.state_version == 1
        assert plan.learner.knowledge_foundation == '完全零基础'
        assert plan.learner.profile_dimensions == frozen['profile']
        with pytest.raises(ValueError, match='identity'):
            KnowledgeService.prepare('循环', user_id=ctx.user_id + 1, learner_context=ctx)
        shadow = {**frozen, 'state_source': 'shadow', 'learner_state': None}
        app.config['LEARNER_STATE_READ_MODE'] = 'evidence'
        assert LearnerContextService.from_resource_snapshot(shadow).mastery == {}


def test_resource_retrieval_filters_private_other_class_and_answers_and_preserves_versions(app):
    with app.app_context():
        materials(app)
        with indexed():
            manifest, passages = Evidence.retrieve(Context.capture(app.config['TEST_STUDENT'], 'loop-for'), '循环边界', Resources._citation('loop-for'))
        assert manifest['status'] == 'retrieved'
        assert {s['chunk_id'] for s in manifest['sources']} == {'public', 'own'}
        assert all(s['version'] == 2 for s in manifest['sources'])
        assert all('SECRET' not in p['content'] for p in passages)
        assert all('content' not in s for s in manifest['sources'])
        assert Evidence.current(app.config['TEST_STUDENT'], manifest)
        changed = deepcopy(manifest); changed['sources'] = []
        assert not Evidence.current(app.config['TEST_STUDENT'], changed)


def test_pipeline_passes_same_sources_to_designer_generator_and_ignores_model_citations(app):
    with app.app_context():
        materials(app)
        original = Resources._generate_from_bundle
        seen = []
        def generator(*args, **kwargs):
            seen.append(deepcopy(args[3]['course_evidence']))
            generated, backend, bundle = original(*args, **kwargs)
            generated[0]['citations'] = [{'document_id': 'forged'}]
            return generated, backend, bundle
        with patch.object(Resources, '_generate_from_bundle', side_effect=generator):
            result = run(app)
        assert seen[0]['status'] == 'retrieved'
        assert {s['chunk_id'] for s in seen[0]['passages']} == {'public', 'own'}
        assert result['course_evidence']['source_count'] == 2
        assert all(c['document_id'] != 'forged' for r in result['resources'] for c in r['citations'])
        assert any(c.get('version') == 2 for c in result['resources'][0]['citations'])
        assert 'invalid_citation' not in result['resources'][0]['risk_reasons']
        assert 'content_hash' not in str(result)
        assert all('_generation_meta' not in r['content'] for r in result['resources'])


@pytest.mark.parametrize('change', ['unpublish', 'version', 'content', 'transfer', 'type'])
def test_revoked_evidence_hides_content_steps_audit_and_recommendations(app, change):
    with app.app_context():
        docs, other, _ = materials(app)
        result = run(app)
        row = ResourceGenerationTask.query.filter_by(task_id=result['task_id']).one()
        row.steps = [{'agent': 'test', 'output_summary': {'text': 'SENSITIVE_DERIVED'}}]
        row.audit_report = {'explanation': 'SENSITIVE_DERIVED'}
        resources = PersonalizedLearningResource.query.filter_by(generation_task_id=row.task_id).all()
        for r in resources:
            r.content = {'text': 'SENSITIVE_DERIVED'}; r.review_status = 'pending_review'
        if change == 'unpublish': docs['own'].published = False
        if change == 'version': docs['own'].version = 3
        if change == 'content': KnowledgeChunk.query.filter_by(chunk_id='own').one().content = 'changed without version'
        if change == 'transfer': db.session.get(User, app.config['TEST_STUDENT']).class_id = other.id
        if change == 'type': KnowledgeChunk.query.filter_by(chunk_id='own').one().knowledge_type = 'solution'
        db.session.commit()
        current = Resources.get_task(app.config['TEST_STUDENT'], row.task_id)
        assert current['course_evidence']['status'] == 'unavailable'
        assert current['resources'] == [] and current['steps'] == [] and current['audit_report'] is None
        assert 'SENSITIVE_DERIVED' not in str(resources[0].to_dict())
        assert not Resources.list_student(app.config['TEST_STUDENT'], {})['items']
        from app.services.recommendation import RecommendationService
        assert RecommendationService.sort_personalized_resources(resources, None) == []
        assert Resources.release_all_pending(app.config['TEST_TEACHER'])['approved_count'] == 0
        assert Resources.release_soft_pending(app.config['TEST_TEACHER'])['approved_count'] == 0
        with pytest.raises(LookupError): Resources.review(resources[0].id, app.config['TEST_TEACHER'], 'approved')
        with pytest.raises(LookupError): Resources.get_audit(resources[0].id)


def test_revocation_during_generation_fails_before_save_even_on_mysql_snapshot(app):
    with app.app_context():
        materials(app)
        task = queued(app)
        original = Resources._generate_from_bundle
        def revoke(*args, **kwargs):
            output = original(*args, **kwargs)
            with Session(db.engine) as session:
                session.get(KnowledgeDocument, 'own').published = False
                session.commit()
            return output
        db.session.rollback()
        with indexed(), patch.object(Resources, '_generate_from_bundle', side_effect=revoke):
            Resources.run_task(app, task['task_id'])
        db.session.rollback()
        result = Resources.get_task(app.config['TEST_STUDENT'], task['task_id'])
        assert result['status'] == 'failed' and not result['resources']
        assert PersonalizedLearningResource.query.filter_by(generation_task_id=task['task_id']).count() == 0


def test_no_evidence_is_explicit_and_retrieval_error_does_not_claim_grounding(app):
    with app.app_context():
        # No READY materials: no vector access, explicit built-in source fallback.
        KnowledgeDocument.query.update({'published': False}); db.session.commit()
        result = run(app)
        assert result['course_evidence']['status'] == 'builtin_only'
        task = queued(app, force_regenerate=True)
        with patch.object(KnowledgeService, 'prepare', side_effect=RuntimeError('retrieval unavailable')):
            Resources.run_task(app, task['task_id'])
        db.session.rollback()
        assert Resources.get_task(app.config['TEST_STUDENT'], task['task_id'])['status'] == 'failed'


def test_protected_evidence_never_creates_public_media_and_teacher_acl_applies(app):
    with app.app_context():
        _, _, other_teacher = materials(app)
        result = run(app)
        row = PersonalizedLearningResource.query.filter_by(generation_task_id=result['task_id']).first()
        row.resource_type = 'audio_explanation'; row.content = {'transcript': 'protected lesson'}
        db.session.commit()
        with patch('app.services.tts_service.TtsService.synthesize_to_media', side_effect=AssertionError('public upload')):
            Resources._hydrate_optional_media(app, result['task_id'])
        db.session.rollback(); db.session.refresh(row)
        assert row.content['media_status'] == 'source_protected' and row.content_url is None
        # The other teacher must not inherit the student's class material access.
        assert not Evidence.resource_current(row, other_teacher.id)
        response = app.test_client().get(f'/api/v1/teacher/personalized-resources/{row.id}/audit', headers=headers(other_teacher.id))
        assert response.status_code == 404


def test_evidence_manifest_migration_is_repeatable_and_does_not_backfill(app):
    path = Path(__file__).parents[1] / 'migrations/versions/20261017_0028_resource_course_evidence.py'
    spec = importlib.util.spec_from_file_location('evidence_migration', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with app.app_context(), db.engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            module.downgrade(); module.upgrade(); module.upgrade()
        assert 'evidence_manifest' in {c['name'] for c in inspect(connection).get_columns('resource_generation_tasks')}


def test_resource_provider_fallback_keeps_actual_model_and_safe_failure(app):
    from agents.llm_client import LLMCallError
    from app.services.pedagogical_resource import build_local_bundle
    primary = ('unused-secret', 'https://api.deepseek.com/v1/chat/completions', 'primary-model')
    backup = ('other-unused', 'https://api.openai.com/v1/chat/completions', 'backup-model')
    with app.app_context():
        with patch('agents.llm_client.llm_provider', return_value=primary), \
             patch('agents.llm_client.openai_provider', return_value=backup), \
             patch('app.services.personalized_resource.llm_bundle', side_effect=[LLMCallError('llm_http_401'), build_local_bundle('loop-for', analysis={}, profile={})]) as generate:
            _, backend, bundle = Resources._generate_from_bundle('loop-for', ['learning_bundle'], {}, {}, require_real_api=True)
        assert backend == 'openai'
        assert bundle['_generation_meta'] == {'model':'backup-model', 'fallback_codes':['llm_http_401']}
        assert [c.kwargs['provider'] for c in generate.call_args_list] == [primary, backup]
        with patch('agents.llm_client.llm_provider', return_value=primary), \
             patch('agents.llm_client.openai_provider', return_value=primary), \
             patch('app.services.personalized_resource.llm_bundle', side_effect=LLMCallError('llm_http_401')) as generate:
            with pytest.raises(RuntimeError, match='llm_http_401'):
                Resources._generate_from_bundle('loop-for', ['learning_bundle'], {}, {}, require_real_api=True)
        assert generate.call_count == 1


def test_strict_model_errors_do_not_expose_provider_body_or_credentials():
    from types import SimpleNamespace
    from agents.llm_client import chat_json, LLMCallError
    import requests
    provider = ('secret-token', 'https://example.invalid', 'test')
    failures = [
        (SimpleNamespace(status_code=401), 'llm_http_401'),
        (SimpleNamespace(status_code=200,json=lambda:{'choices':[{'finish_reason':'length','message':{'content':'secret'}}]}), 'llm_output_truncated'),
        (SimpleNamespace(status_code=200,json=lambda:{'choices':[{'message':{'content':'not json'}}]}), 'llm_json_invalid'),
    ]
    for response, code in failures:
        with patch('agents.llm_client.direct_post', return_value=response):
            assert chat_json(system='s',user='u',provider=provider) is None
            with pytest.raises(LLMCallError,match=code):
                chat_json(system='s',user='u',provider=provider,raise_on_error=True)
    with patch('agents.llm_client.direct_post',side_effect=requests.Timeout('secret-token')):
        with pytest.raises(LLMCallError,match='^llm_timeout$'):
            chat_json(system='s',user='u',provider=provider,raise_on_error=True)
