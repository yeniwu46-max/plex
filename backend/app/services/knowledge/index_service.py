# -*- coding: utf-8 -*-
"""文档注册 + 异步索引状态机（PENDING → PARSING → CHUNKING → EMBEDDING → INDEXING → READY / FAILED）。

版本管理：重新索引时 version+1，新 chunk 与向量写入成功后再删除旧版本，失败保留旧版本可检索。
"""
from __future__ import annotations

import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.data.course_knowledge import DOMAIN_SOURCE_FILES, KNOWLEDGE_ROOT
from app.data.knowledge_node_registry import KNOWLEDGE_DOMAINS
from app.models import KnowledgeChunk, KnowledgeConcept, KnowledgeDocument, KnowledgeIndexJob, db
from app.models.knowledge_document import INDEX_STATUSES, RESOURCE_TYPES
from app.services.file_upload import _validate_content_signature
from app.utils.time import utc_now

from .chunk_service import ChunkService
from .graph_service import GraphService
from .lexical_index import LexicalIndex
from .parser_service import ParserError, ParserService, detect_file_type
from .settings import knowledge_env, retrieval_config
from .text_utils import content_hash
from .vector_service import VectorService

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='plex-knowledge-index')
ALLOWED_UPLOAD_TYPES = {'md', 'markdown', 'txt', 'pdf', 'docx', 'pptx', 'json'}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
RUNNING_STATUSES = {'PENDING', 'PARSING', 'CHUNKING', 'EMBEDDING', 'INDEXING'}


class DocumentValidationError(ValueError):
    pass


class IndexService:
    # ------------------------------------------------------------------ storage
    @staticmethod
    def _document_root() -> Path:
        root = Path(current_app.instance_path) / 'knowledge' / 'documents'
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _should_run_sync() -> bool:
        return bool(current_app.config.get('TESTING')) or knowledge_env()['index_sync']

    # ------------------------------------------------------------------ registration
    @staticmethod
    def register_upload(
        file: FileStorage,
        *,
        user_id: int,
        title: str | None = None,
        course_id: str | None = None,
        chapter: str = '',
        resource_type: str = 'textbook',
        audience_level: str = 'beginner',
        teacher_verified: bool = False,
        concept_hints: list[str] | None = None,
        auto_index: bool = True,
    ) -> KnowledgeDocument:
        if not file or not file.filename:
            raise DocumentValidationError('未选择文件')
        file_type = detect_file_type(file.filename, fallback='')
        if file_type not in ALLOWED_UPLOAD_TYPES:
            raise DocumentValidationError('仅支持 md / txt / pdf / docx / pptx / json')
        data = file.read()
        if not data:
            raise DocumentValidationError('上传文件不能为空')
        if len(data) > MAX_UPLOAD_BYTES:
            raise DocumentValidationError('文件大小超过 100 MB 上限')
        _validate_content_signature(f'.{file_type}', data)
        checksum = hashlib.sha256(data).hexdigest()
        safe_name = secure_filename(file.filename) or f'document.{file_type}'
        stored = IndexService._document_root() / f'{uuid.uuid4().hex[:12]}_{safe_name}'
        stored.write_bytes(data)
        return IndexService._create_document(
            title=title or Path(file.filename).stem,
            file_name=file.filename,
            file_path=str(stored),
            file_type=file_type,
            file_size=len(data),
            checksum=checksum,
            course_id=course_id,
            chapter=chapter,
            resource_type=resource_type,
            audience_level=audience_level,
            source='upload',
            uploaded_by=user_id,
            teacher_verified=teacher_verified,
            concept_hints=concept_hints,
            auto_index=auto_index,
        )

    @staticmethod
    def register_text(
        *,
        title: str,
        text: str,
        user_id: int | None,
        course_id: str | None = None,
        chapter: str = '',
        resource_type: str = 'markdown',
        audience_level: str = 'beginner',
        source: str = 'manual',
        teacher_verified: bool = False,
        quality_score: float | None = None,
        concept_hints: list[str] | None = None,
        meta: dict[str, Any] | None = None,
        auto_index: bool = True,
        file_type: str = 'md',
    ) -> KnowledgeDocument:
        text = (text or '').strip()
        if len(text) < 20:
            raise DocumentValidationError('文本内容过短')
        data = text.encode('utf-8')
        stored = IndexService._document_root() / f'{uuid.uuid4().hex[:12]}_{secure_filename(title)[:60] or "text"}.{file_type}'
        stored.write_bytes(data)
        return IndexService._create_document(
            title=title,
            file_name=stored.name,
            file_path=str(stored),
            file_type=file_type,
            file_size=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            course_id=course_id,
            chapter=chapter,
            resource_type=resource_type,
            audience_level=audience_level,
            source=source,
            uploaded_by=user_id,
            teacher_verified=teacher_verified,
            quality_score=quality_score,
            concept_hints=concept_hints,
            meta=meta,
            auto_index=auto_index,
        )

    @staticmethod
    def _create_document(**fields: Any) -> KnowledgeDocument:
        auto_index = fields.pop('auto_index', True)
        concept_hints = fields.pop('concept_hints', None) or []
        quality_score = fields.pop('quality_score', None)
        resource_type = fields.get('resource_type') or 'markdown'
        if resource_type not in RESOURCE_TYPES:
            raise DocumentValidationError(f'未知资源类型 {resource_type}')
        meta = dict(fields.pop('meta', None) or {})
        if concept_hints:
            meta['concept_hints'] = list(concept_hints)
        doc = KnowledgeDocument(
            title=(fields.get('title') or '未命名文档')[:200],
            file_name=(fields.get('file_name') or '')[:255],
            file_path=fields.get('file_path'),
            file_type=fields.get('file_type') or 'md',
            file_size=fields.get('file_size') or 0,
            checksum=fields.get('checksum'),
            course_id=fields.get('course_id') or retrieval_config().get('course_id', 'python-basics'),
            chapter=(fields.get('chapter') or '')[:120],
            resource_type=resource_type,
            source=fields.get('source') or 'upload',
            audience_level=fields.get('audience_level') or 'beginner',
            uploaded_by=fields.get('uploaded_by'),
            teacher_verified=bool(fields.get('teacher_verified')),
            verified_by=fields.get('uploaded_by') if fields.get('teacher_verified') else None,
            verified_at=utc_now() if fields.get('teacher_verified') else None,
            quality_score=float(quality_score) if quality_score is not None else (0.85 if fields.get('teacher_verified') else 0.6),
            status='PENDING',
            meta=meta,
        )
        db.session.add(doc)
        db.session.commit()
        if auto_index:
            IndexService.start_index(doc.id, user_id=fields.get('uploaded_by'))
        return doc

    # ------------------------------------------------------------------ builtin course docs
    @staticmethod
    def register_builtin_docs(*, index: bool = True) -> dict[str, int]:
        """把 backend/data/rag_docs 课程知识库注册为内建、教师审核过的文档（按 checksum 幂等）。"""
        stats = {'registered': 0, 'unchanged': 0, 'reindexed': 0}
        for domain in KNOWLEDGE_DOMAINS:
            filename = DOMAIN_SOURCE_FILES.get(domain.key)
            path = KNOWLEDGE_ROOT / filename if filename else None
            if not path or not path.is_file():
                continue
            data = path.read_bytes()
            checksum = hashlib.sha256(data).hexdigest()
            existing = KnowledgeDocument.query.filter_by(source='builtin', file_name=filename).first()
            if existing and existing.checksum == checksum and existing.status == 'READY':
                stats['unchanged'] += 1
                continue
            if existing:
                existing.checksum = checksum
                existing.file_path = str(path)
                existing.file_size = len(data)
                existing.title = f'{domain.title}（课程知识库）'
                db.session.commit()
                if index:
                    IndexService.start_index(existing.id, user_id=None)
                stats['reindexed'] += 1
                continue
            doc = KnowledgeDocument(
                title=f'{domain.title}（课程知识库）',
                file_name=filename,
                file_path=str(path),
                file_type='md',
                file_size=len(data),
                checksum=checksum,
                course_id=retrieval_config().get('course_id', 'python-basics'),
                chapter=domain.title,
                resource_type='textbook',
                source='builtin',
                audience_level='beginner',
                teacher_verified=True,
                verified_at=utc_now(),
                quality_score=0.9,
                status='PENDING',
                meta={'domain_key': domain.key, 'builtin': True},
            )
            db.session.add(doc)
            db.session.commit()
            if index:
                IndexService.start_index(doc.id, user_id=None)
            stats['registered'] += 1
        return stats

    # ------------------------------------------------------------------ jobs
    @staticmethod
    def start_index(document_id: str, *, user_id: int | None = None, sync: bool | None = None) -> KnowledgeIndexJob:
        doc = db.session.get(KnowledgeDocument, document_id)
        if not doc:
            raise DocumentValidationError('文档不存在')
        running = KnowledgeIndexJob.query.filter(
            KnowledgeIndexJob.document_id == document_id, KnowledgeIndexJob.status.in_(list(RUNNING_STATUSES))
        ).first()
        if running and running.created_at and running.created_at > utc_now() - timedelta(minutes=10):
            return running
        job = KnowledgeIndexJob(
            document_id=document_id,
            version=doc.version + (1 if doc.status == 'READY' or doc.chunk_count else 0),
            status='PENDING',
            stage='PENDING',
            triggered_by=user_id,
        )
        doc.status = 'PENDING'
        doc.stage_progress = 0
        doc.error_message = None
        db.session.add(job)
        db.session.commit()
        app = current_app._get_current_object()
        run_sync = IndexService._should_run_sync() if sync is None else sync
        if run_sync:
            IndexService.run_index(app, job.id)
            db.session.expire_all()
        else:
            _EXECUTOR.submit(IndexService.run_index, app, job.id)
        return db.session.get(KnowledgeIndexJob, job.id)

    @staticmethod
    def run_index(app, job_id: str) -> None:
        with app.app_context():
            job = db.session.get(KnowledgeIndexJob, job_id)
            if not job:
                return
            doc = db.session.get(KnowledgeDocument, job.document_id)
            if not doc:
                job.status = 'FAILED'
                job.error_message = 'document missing'
                db.session.commit()
                return
            try:
                IndexService._pipeline(job, doc)
            except Exception as exc:  # noqa: BLE001 - 记录失败原因供重试
                db.session.rollback()
                job = db.session.get(KnowledgeIndexJob, job_id)
                doc = db.session.get(KnowledgeDocument, job.document_id)
                message = f'{type(exc).__name__}: {exc}'[:2000]
                job.status = 'FAILED'
                job.error_message = message
                job.finished_at = utc_now()
                doc.status = 'FAILED'
                doc.error_message = message
                db.session.commit()
                app.logger.warning('knowledge index failed doc=%s job=%s: %s', doc.id, job.id, message)

    @staticmethod
    def _set_stage(job: KnowledgeIndexJob, doc: KnowledgeDocument, stage: str, progress: int) -> None:
        assert stage in INDEX_STATUSES
        job.status = stage
        job.stage = stage
        job.progress = progress
        doc.status = stage
        doc.stage_progress = progress
        db.session.commit()

    @staticmethod
    def _pipeline(job: KnowledgeIndexJob, doc: KnowledgeDocument) -> None:
        job.started_at = utc_now()
        vector = VectorService()
        job.embedding_provider = vector.embedding.provider.identifier
        job.vector_backend = vector.store.backend

        # 1. Parsing
        IndexService._set_stage(job, doc, 'PARSING', 10)
        if not doc.file_path or not Path(doc.file_path).is_file():
            raise ParserError('文档源文件缺失，请重新上传')
        parsed = ParserService.parse_path(Path(doc.file_path), doc.file_type, doc.title)

        # 2. Chunking（含清洗、metadata、概念映射）
        IndexService._set_stage(job, doc, 'CHUNKING', 30)
        lexicon = GraphService.concept_lexicon()
        chunker = ChunkService(lexicon)
        default_difficulty = {'beginner': 2, 'intermediate': 3, 'advanced': 4}.get(doc.audience_level or 'beginner', 2)
        drafts = chunker.chunk_markdown(
            parsed.markdown,
            title=doc.title,
            default_difficulty=default_difficulty,
            concept_hints=list((doc.meta or {}).get('concept_hints') or []),
        )
        if not drafts:
            raise ParserError('未能从文档中切分出有效内容')
        new_version = job.version
        new_rows: list[KnowledgeChunk] = []
        for draft in drafts:
            new_rows.append(
                KnowledgeChunk(
                    document_id=doc.id,
                    version=new_version,
                    sequence=draft.sequence,
                    title=draft.title[:255],
                    content=draft.content,
                    content_hash=content_hash(draft.content),
                    knowledge_type=draft.knowledge_type,
                    concept_ids=list(draft.concept_ids),
                    primary_concept_id=draft.primary_concept_id,
                    course_id=doc.course_id,
                    chapter=doc.chapter or ' › '.join(draft.meta.get('heading_path', [])[:1]),
                    difficulty=draft.difficulty,
                    resource_type=doc.resource_type,
                    source=(doc.file_name or doc.title)[:255],
                    source_page=draft.source_page,
                    audience_level=doc.audience_level,
                    teacher_verified=bool(doc.teacher_verified),
                    token_count=draft.token_count,
                    embedding_status='PENDING',
                    status='staging',
                    meta=draft.meta,
                )
            )
        db.session.add_all(new_rows)
        job.chunk_count = len(new_rows)
        db.session.commit()

        # 3. Embedding + 4. Indexing（先写新版本，再淘汰旧版本）
        IndexService._set_stage(job, doc, 'EMBEDDING', 55)
        concept_names = {row.concept_id: row.name for row in KnowledgeConcept.query.filter(KnowledgeConcept.node_type.in_(('concept', 'skill'))).all()}
        indexed = vector.index_chunks(new_rows, concept_names)
        job.embedded_count = indexed
        db.session.commit()

        IndexService._set_stage(job, doc, 'INDEXING', 85)
        old_rows = KnowledgeChunk.query.filter(
            KnowledgeChunk.document_id == doc.id, KnowledgeChunk.version != new_version
        ).all()
        if old_rows:
            vector.remove_chunks([row.chunk_id for row in old_rows])
            for row in old_rows:
                db.session.delete(row)
        for row in new_rows:
            row.status = 'active'
        concept_ids: list[str] = []
        for row in new_rows:
            for cid in row.concept_ids or []:
                if cid not in concept_ids:
                    concept_ids.append(cid)
        doc.version = new_version
        doc.chunk_count = len(new_rows)
        doc.concept_ids = concept_ids[:64]
        doc.indexed_at = utc_now()
        doc.error_message = None
        job.finished_at = utc_now()
        IndexService._set_stage(job, doc, 'READY', 100)
        LexicalIndex.invalidate()

    # ------------------------------------------------------------------ maintenance
    @staticmethod
    def delete_document(document_id: str) -> bool:
        doc = db.session.get(KnowledgeDocument, document_id)
        if not doc:
            return False
        VectorService().remove_document(document_id)
        path, source = doc.file_path, doc.source
        # 显式删除子表：SQLite 默认不执行 ON DELETE CASCADE
        KnowledgeChunk.query.filter_by(document_id=document_id).delete(synchronize_session=False)
        KnowledgeIndexJob.query.filter_by(document_id=document_id).delete(synchronize_session=False)
        db.session.delete(doc)
        db.session.commit()
        LexicalIndex.invalidate()
        if path and source != 'builtin':
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
        return True

    @staticmethod
    def verify_document(
        document_id: str,
        *,
        user_id: int,
        verified: bool = True,
        quality_score: float | None = None,
    ) -> KnowledgeDocument | None:
        doc = db.session.get(KnowledgeDocument, document_id)
        if not doc:
            return None
        doc.teacher_verified = bool(verified)
        doc.verified_by = user_id if verified else None
        doc.verified_at = utc_now() if verified else None
        if quality_score is not None:
            doc.quality_score = max(0.0, min(1.0, float(quality_score)))
        chunks = KnowledgeChunk.query.filter_by(document_id=document_id, status='active').all()
        for chunk in chunks:
            chunk.teacher_verified = bool(verified)
        db.session.commit()
        # 同步向量库 metadata（复用已有向量，不重新 embedding）
        vector = VectorService()
        records = vector.store.get([c.chunk_id for c in chunks])
        if records:
            from .providers.vector_store import VectorRecord

            vector.store.upsert(
                [VectorRecord(id=c.chunk_id, vector=records[c.chunk_id].vector, metadata=c.metadata_dict()) for c in chunks if c.chunk_id in records]
            )
        LexicalIndex.invalidate()
        return doc

    @staticmethod
    def update_document(document_id: str, **fields: Any) -> KnowledgeDocument | None:
        doc = db.session.get(KnowledgeDocument, document_id)
        if not doc:
            return None
        allowed = {'title', 'chapter', 'resource_type', 'audience_level', 'quality_score', 'course_id'}
        for key, value in fields.items():
            if key in allowed and value is not None:
                setattr(doc, key, value)
        db.session.commit()
        return doc

    @staticmethod
    def index_status() -> dict[str, Any]:
        counts = {status: 0 for status in INDEX_STATUSES}
        for status, count in db.session.query(KnowledgeDocument.status, db.func.count(KnowledgeDocument.id)).group_by(KnowledgeDocument.status).all():
            counts[status] = int(count)
        chunk_total = KnowledgeChunk.query.filter_by(status='active').count()
        embedded = KnowledgeChunk.query.filter_by(status='active', embedding_status='READY').count()
        running = KnowledgeIndexJob.query.filter(KnowledgeIndexJob.status.in_(list(RUNNING_STATUSES))).order_by(KnowledgeIndexJob.created_at.desc()).all()
        recent_failed = KnowledgeIndexJob.query.filter_by(status='FAILED').order_by(KnowledgeIndexJob.updated_at.desc()).limit(5).all()
        vector = VectorService()
        concept_total = KnowledgeConcept.query.filter_by(status='active').count()
        return {
            'documents': counts,
            'document_total': sum(counts.values()),
            'chunk_total': chunk_total,
            'chunk_embedded': embedded,
            'concept_total': concept_total,
            'vector': vector.describe(),
            'running_jobs': [job.to_dict() for job in running],
            'recent_failed': [job.to_dict() for job in recent_failed],
            'async_mode': not IndexService._should_run_sync(),
        }

    @staticmethod
    def recover_stale_jobs(app) -> int:
        """服务重启后把中断的索引任务标记为 FAILED，保留错误信息以便重试。"""
        with app.app_context():
            cutoff = utc_now() - timedelta(minutes=15)
            rows = KnowledgeIndexJob.query.filter(
                KnowledgeIndexJob.status.in_(list(RUNNING_STATUSES)), KnowledgeIndexJob.created_at < cutoff
            ).all()
            for job in rows:
                job.status = 'FAILED'
                job.error_message = '索引任务因服务重启而中断，请重新索引'
                job.finished_at = utc_now()
                doc = db.session.get(KnowledgeDocument, job.document_id)
                if doc and doc.status in RUNNING_STATUSES:
                    doc.status = 'FAILED'
                    doc.error_message = job.error_message
            if rows:
                db.session.commit()
            return len(rows)

    @staticmethod
    def repair_missing_vectors(*, user_id: int | None = None) -> dict[str, int]:
        """一致性校验：MySQL 中 READY 的文档若在向量库里缺向量（换后端/换 embedding 模型/目录丢失），自动重新索引。"""
        vector = VectorService()
        current_model = vector.embedding.provider.identifier
        checked = repaired = 0
        for doc in KnowledgeDocument.query.filter_by(status='READY').all():
            rows = KnowledgeChunk.query.filter_by(document_id=doc.id, status='active').with_entities(
                KnowledgeChunk.chunk_id, KnowledgeChunk.embedding_model
            ).all()
            checked += 1
            if not rows:
                continue
            ids = [row.chunk_id for row in rows]
            model_changed = any(row.embedding_model and row.embedding_model != current_model for row in rows)
            missing = set(ids) - vector.store.existing_ids(ids)
            if missing or model_changed:
                IndexService.start_index(doc.id, user_id=user_id)
                repaired += 1
        return {'checked': checked, 'reindexed': repaired}

    # ------------------------------------------------------------------ queries
    @staticmethod
    def list_documents(
        *,
        status: str | None = None,
        course_id: str | None = None,
        source: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ):
        query = KnowledgeDocument.query
        if status:
            query = query.filter(KnowledgeDocument.status == status)
        if course_id:
            query = query.filter(KnowledgeDocument.course_id == course_id)
        if source:
            query = query.filter(KnowledgeDocument.source == source)
        if keyword:
            like = f'%{keyword.strip()}%'
            query = query.filter(db.or_(KnowledgeDocument.title.ilike(like), KnowledgeDocument.file_name.ilike(like)))
        return query.order_by(KnowledgeDocument.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def list_chunks(document_id: str, *, page: int = 1, per_page: int = 50, knowledge_type: str | None = None):
        query = KnowledgeChunk.query.filter_by(document_id=document_id, status='active')
        if knowledge_type:
            query = query.filter(KnowledgeChunk.knowledge_type == knowledge_type)
        return query.order_by(KnowledgeChunk.sequence.asc()).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def latest_job(document_id: str) -> KnowledgeIndexJob | None:
        return KnowledgeIndexJob.query.filter_by(document_id=document_id).order_by(KnowledgeIndexJob.created_at.desc()).first()
