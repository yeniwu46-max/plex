"""Versioned course evidence for resource tasks; authorization remains live.

Only server-created snapshots enter retrieval. A manifest records all materials
provided to downstream agents, not a claim that every generated sentence is true.
"""
from copy import deepcopy
import hashlib
import json

from flask import has_request_context
from sqlalchemy.orm import Session

from app.models import db, KnowledgeChunk, ResourceGenerationTask
from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.knowledge.learner_context_service import LearnerContextService
from app.services.knowledge.access_service import KnowledgeAccessService
from app.services.resource_learning_context import ResourceLearningContext

POLICY = 'resource-course-evidence-v1'
UNAVAILABLE = '课程材料已更新或当前无权访问，请重新生成资源。'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


class ResourceCourseEvidence:
    @staticmethod
    def retrieve(snapshot, label, builtin):
        ResourceLearningContext.authorize(snapshot)
        learner = LearnerContextService.from_resource_snapshot(snapshot)
        # prepare performs hybrid retrieval/rerank/context selection, without generation.
        plan = KnowledgeService.prepare(label, user_id=snapshot['user_id'],
            scene='resource', context=learner.current_task, learner_context=learner)
        selected = {s['chunk_id'] for s in plan.context.source_index}
        sources, passages, remaining = [], [], 9000
        if plan.blocked_reason:
            raise ValueError('课程检索请求未通过检查')
        if plan.knowledge_grounded:
            for chunk in plan.chunks:
                if chunk.chunk_id not in selected or remaining <= 0:
                    continue
                text = chunk.content[:min(2200, remaining)]
                source = {
                    'kind': 'course_chunk', 'document_id': chunk.document_id,
                    'chunk_id': chunk.chunk_id, 'version': chunk.version,
                    'title': chunk.title or chunk.document_title, 'section': chunk.chapter,
                    'source_page': chunk.source_page, 'teacher_verified': chunk.teacher_verified,
                    'url': f'/api/v1/rag/sources/{chunk.chunk_id}?version={chunk.version}',
                    'snippet': text[:160], 'content_hash': hashlib.sha256(chunk.content.encode()).hexdigest(),
                }
                sources.append(source)
                passages.append({'chunk_id': chunk.chunk_id, 'version': chunk.version,
                                 'title': source['title'], 'content': text})
                remaining -= len(text)
        payload = {
            'policy_version': POLICY, 'user_id': snapshot['user_id'],
            'status': 'retrieved' if sources else 'builtin_only',
            'sources': sources, 'builtin_citation': deepcopy(builtin),
            'state_source': learner.state_source, 'state_version': learner.state_version,
            'profile_version': snapshot['profile_version'],
            'prerequisite_gaps': list(plan.retrieval.graph.unmet_prerequisites),
        }
        manifest = {**payload, 'digest': digest(payload)}
        ResourceCourseEvidence.require(snapshot['user_id'], manifest)
        return manifest, passages

    @staticmethod
    def valid(manifest):
        if not isinstance(manifest, dict) or manifest.get('policy_version') != POLICY:
            return False
        body = {k: v for k, v in manifest.items() if k != 'digest'}
        return (manifest.get('digest') == digest(body)
                and manifest.get('status') in {'retrieved', 'builtin_only'}
                and isinstance(manifest.get('sources'), list))

    @staticmethod
    def current(user_id, manifest, viewer_id=None):
        if manifest is None:  # Historical tasks did not retain course provenance.
            return True
        if not ResourceCourseEvidence.valid(manifest) or manifest.get('user_id') != user_id:
            return False
        sources = manifest['sources']
        with Session(db.engine) as session:
            owner = KnowledgeAccessService.actor(user_id, session)
            if not owner or owner.status != 'active' or KnowledgeAccessService.role(owner) != 'student':
                return False
            for uid in {user_id, viewer_id or user_id}:
                rows = KnowledgeAccessService.chunks(uid, session=session).filter(
                    KnowledgeChunk.chunk_id.in_([s['chunk_id'] for s in sources])).all()
                actual = {(r.document_id, r.chunk_id, r.version): hashlib.sha256(r.content.encode()).hexdigest() for r in rows}
                if any(actual.get((s['document_id'], s['chunk_id'], s['version'])) != s['content_hash'] for s in sources):
                    return False
        return True

    @staticmethod
    def require(user_id, manifest, viewer_id=None):
        if not ResourceCourseEvidence.current(user_id, manifest, viewer_id):
            raise ValueError(UNAVAILABLE)

    @staticmethod
    def viewer():
        if has_request_context():
            from flask_jwt_extended import get_jwt_identity
            try:
                identity = get_jwt_identity()
            except RuntimeError:  # Internal code can execute in an unauthenticated request context.
                return None
            return int(identity) if identity else None
        return None

    @staticmethod
    def for_resource(row):
        task = ResourceGenerationTask.query.filter_by(task_id=row.generation_task_id).first()
        return task.evidence_manifest if task else None

    @staticmethod
    def resource_current(row, viewer_id=None):
        manifest = ResourceCourseEvidence.for_resource(row)
        return ResourceCourseEvidence.current(row.user_id, manifest, viewer_id or ResourceCourseEvidence.viewer())

    @staticmethod
    def require_resource(row, viewer_id=None):
        if not ResourceCourseEvidence.resource_current(row, viewer_id):
            raise LookupError(UNAVAILABLE)

    @staticmethod
    def citations(manifest):
        # Provenance is server-owned. Model-declared citations are never accepted.
        return [deepcopy(manifest['builtin_citation']), *[
            {k: v for k, v in source.items() if k != 'content_hash'} for source in manifest['sources']]]

    @staticmethod
    def summary(manifest, user_id, viewer_id=None):
        if manifest is None:
            return None
        if not ResourceCourseEvidence.current(user_id, manifest, viewer_id):
            return {'status': 'unavailable', 'message': UNAVAILABLE, 'sources': []}
        return {
            'status': manifest['status'], 'policy_version': POLICY,
            'source_count': len(manifest['sources']), 'digest': manifest['digest'],
            'sources': ResourceCourseEvidence.citations(manifest),
            'message': ('已结合当前有权访问的课程材料；来源不等于逐句正确性保证。'
                        if manifest['sources'] else '课程检索证据不足，本次仅使用内置课程材料。'),
        }
