# -*- coding: utf-8 -*-
"""Knowledge Intelligence Layer：知识文档、Chunk 元数据、索引任务。

MySQL 只保存业务元数据与 Chunk 文本/metadata；embedding 向量存放于 VectorStore（以 chunk_id 关联）。
"""
from __future__ import annotations

import uuid

from app.utils.time import utc_now

from .base import db

INDEX_STATUSES = ('PENDING', 'PARSING', 'CHUNKING', 'EMBEDDING', 'INDEXING', 'READY', 'FAILED')

KNOWLEDGE_TYPES = (
    'concept_explanation',
    'example',
    'exercise',
    'solution',
    'misconception',
    'summary',
    'extension',
    'teacher_note',
)

RESOURCE_TYPES = (
    'textbook',
    'slides',
    'markdown',
    'exercise',
    'mistake_analysis',
    'teacher_resource',
    'ai_generated',
    'other',
)


def _new_id() -> str:
    return uuid.uuid4().hex


class KnowledgeDocument(db.Model):
    __tablename__ = 'knowledge_documents'

    id = db.Column(db.String(32), primary_key=True, default=_new_id)
    title = db.Column(db.String(200), nullable=False)
    file_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    file_type = db.Column(db.String(16), nullable=False, default='md')  # md|txt|pdf|docx|pptx|json
    file_size = db.Column(db.Integer, default=0)
    checksum = db.Column(db.String(64), index=True)
    course_id = db.Column(db.String(64), nullable=False, default='python-basics', index=True)
    chapter = db.Column(db.String(120), default='')
    resource_type = db.Column(db.String(32), nullable=False, default='markdown')
    source = db.Column(db.String(64), default='upload')  # upload|builtin|platform_resource|ai_generated
    audience_level = db.Column(db.String(24), default='beginner')  # beginner|intermediate|advanced|all
    uploaded_by = db.Column(db.Integer, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(16), nullable=False, default='PENDING', index=True)
    stage_progress = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text)
    chunk_count = db.Column(db.Integer, nullable=False, default=0)
    concept_ids = db.Column(db.JSON)
    teacher_verified = db.Column(db.Boolean, nullable=False, default=False)
    verified_by = db.Column(db.Integer)
    verified_at = db.Column(db.DateTime)
    quality_score = db.Column(db.Float, nullable=False, default=0.6)  # 0-1 资源质量（教师可调整）
    meta = db.Column(db.JSON)
    indexed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    chunks = db.relationship(
        'KnowledgeChunk',
        backref='document',
        lazy='dynamic',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size or 0,
            'checksum': self.checksum,
            'course_id': self.course_id,
            'chapter': self.chapter or '',
            'resource_type': self.resource_type,
            'source': self.source,
            'audience_level': self.audience_level,
            'uploaded_by': self.uploaded_by,
            'version': self.version,
            'status': self.status,
            'stage_progress': self.stage_progress,
            'error_message': self.error_message,
            'chunk_count': self.chunk_count,
            'concept_ids': list(self.concept_ids or []),
            'teacher_verified': bool(self.teacher_verified),
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'quality_score': self.quality_score,
            'meta': self.meta or {},
            'indexed_at': self.indexed_at.isoformat() if self.indexed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeChunk(db.Model):
    __tablename__ = 'knowledge_chunks'

    chunk_id = db.Column(db.String(32), primary_key=True, default=_new_id)
    document_id = db.Column(
        db.String(32), db.ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False, index=True
    )
    version = db.Column(db.Integer, nullable=False, default=1)
    sequence = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(255), default='')
    content = db.Column(db.Text, nullable=False)
    content_hash = db.Column(db.String(64), index=True)
    knowledge_type = db.Column(db.String(32), nullable=False, default='concept_explanation', index=True)
    concept_ids = db.Column(db.JSON)
    primary_concept_id = db.Column(db.String(64), index=True)
    course_id = db.Column(db.String(64), nullable=False, default='python-basics', index=True)
    chapter = db.Column(db.String(120), default='')
    difficulty = db.Column(db.Integer, nullable=False, default=2)
    resource_type = db.Column(db.String(32), nullable=False, default='markdown')
    source = db.Column(db.String(255))
    source_page = db.Column(db.Integer)
    audience_level = db.Column(db.String(24), default='beginner')
    teacher_verified = db.Column(db.Boolean, nullable=False, default=False)
    token_count = db.Column(db.Integer, nullable=False, default=0)
    embedding_status = db.Column(db.String(16), nullable=False, default='PENDING')  # PENDING|READY|FAILED
    embedding_model = db.Column(db.String(80))
    status = db.Column(db.String(16), nullable=False, default='active', index=True)  # active|stale
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def metadata_dict(self) -> dict:
        """写入 VectorStore 的检索 metadata（不含正文全文）。"""
        return {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'course_id': self.course_id,
            'chapter': self.chapter or '',
            'concept_ids': list(self.concept_ids or []),
            'primary_concept_id': self.primary_concept_id or '',
            'knowledge_type': self.knowledge_type,
            'difficulty': self.difficulty,
            'resource_type': self.resource_type,
            'title': self.title or '',
            'source': self.source or '',
            'source_page': self.source_page,
            'teacher_verified': bool(self.teacher_verified),
            'version': self.version,
            'audience_level': self.audience_level,
        }

    def to_dict(self, include_content: bool = True, preview_chars: int | None = None) -> dict:
        payload = self.metadata_dict()
        payload.update(
            {
                'sequence': self.sequence,
                'content_hash': self.content_hash,
                'token_count': self.token_count,
                'embedding_status': self.embedding_status,
                'embedding_model': self.embedding_model,
                'status': self.status,
                'meta': self.meta or {},
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }
        )
        if include_content:
            payload['content'] = self.content
        elif preview_chars:
            text = self.content or ''
            payload['preview'] = text[:preview_chars] + ('…' if len(text) > preview_chars else '')
        return payload


class KnowledgeIndexJob(db.Model):
    __tablename__ = 'knowledge_index_jobs'

    id = db.Column(db.String(32), primary_key=True, default=_new_id)
    document_id = db.Column(
        db.String(32), db.ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False, index=True
    )
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(16), nullable=False, default='PENDING', index=True)
    stage = db.Column(db.String(16), nullable=False, default='PENDING')
    progress = db.Column(db.Integer, nullable=False, default=0)
    chunk_count = db.Column(db.Integer, nullable=False, default=0)
    embedded_count = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text)
    triggered_by = db.Column(db.Integer)
    embedding_provider = db.Column(db.String(64))
    vector_backend = db.Column(db.String(32))
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'document_id': self.document_id,
            'version': self.version,
            'status': self.status,
            'stage': self.stage,
            'progress': self.progress,
            'chunk_count': self.chunk_count,
            'embedded_count': self.embedded_count,
            'error_message': self.error_message,
            'triggered_by': self.triggered_by,
            'embedding_provider': self.embedding_provider,
            'vector_backend': self.vector_backend,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
