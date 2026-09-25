# -*- coding: utf-8 -*-
"""RAG 知识库门面（兼容层）。

历史上这里是 Mock / LlamaIndex 可切换实现；现在统一委托给 Knowledge Intelligence Layer
（``app.services.knowledge.KnowledgeService``），保留原有返回结构以兼容 ``/kb/*`` 路由、
健康检查与资源审核等旧调用方。业务实现请看 ``app/services/knowledge``。
"""
from __future__ import annotations

from typing import Any

from app.services.course_safety import CourseSafetyService
from app.utils.time import utc_now

DEFAULT_ANSWER = '课程知识库中暂无足够依据回答该问题，建议先查阅对应章节或换个说法。'


def _knowledge_service():
    from app.services.knowledge import KnowledgeService

    return KnowledgeService


class RagService:
    @staticmethod
    def backend_name() -> str:
        try:
            from app.services.knowledge.providers.vector_store import get_vector_store

            return f'graph-rag:{get_vector_store().backend}'
        except Exception:  # noqa: BLE001
            return 'graph-rag'

    @staticmethod
    def upload(filename: str) -> dict:
        """旧接口仅返回受理信息；实际导入请使用 POST /api/v1/knowledge/documents。"""
        task_id = 'task_' + utc_now().strftime('%Y%m%d%H%M%S')
        return {
            'task_id': task_id,
            'filename': filename,
            'status': 'accepted',
            'estimated_time': '—',
            'backend': RagService.backend_name(),
            'hint': '请通过 /api/v1/knowledge/documents 上传并索引文档',
        }

    @staticmethod
    def query(question: str, *, user_id: int | None = None, role: str = 'student') -> dict:
        """兼容旧结构：answer / sources[{doc_id, score, snippet}] / confidence / backend。"""
        CourseSafetyService.ensure_safe(question, enforce_course_scope=True)
        answer = _knowledge_service().answer(question, user_id=user_id, role=role, scene='chat')
        sources = [
            {
                'doc_id': s.get('document_id'),
                'chunk_id': s.get('chunk_id'),
                'title': s.get('title') or s.get('document_title'),
                'knowledge_type': s.get('knowledge_type'),
                'teacher_verified': bool(s.get('teacher_verified')),
                'snippet': s.get('preview') or '',
            }
            for s in answer.sources
        ]
        return {
            'answer': answer.answer if answer.knowledge_grounded else (answer.answer or DEFAULT_ANSWER),
            'sources': sources,
            'confidence': round(float(answer.confidence), 3),
            'confidence_level': answer.confidence_level,
            'knowledge_grounded': answer.knowledge_grounded,
            'concepts': answer.concepts,
            'recommended_next': answer.recommended_next,
            'teaching_strategy': answer.teaching_strategy,
            'backend': RagService.backend_name(),
        }

    @staticmethod
    def list_documents() -> dict:
        from app.services.knowledge.index_service import IndexService

        pagination = IndexService.list_documents(page=1, per_page=100)
        documents = [
            {
                'id': d.id,
                'name': d.title,
                'size': d.file_size,
                'type': d.file_type,
                'status': 'indexed' if d.status == 'READY' else ('failed' if d.status == 'FAILED' else 'processing'),
                'index_status': d.status,
                'chunk_count': d.chunk_count,
                'uploaded_at': d.created_at.isoformat() if d.created_at else None,
                'uploader': d.uploaded_by,
                'source': d.source,
                'teacher_verified': bool(d.teacher_verified),
            }
            for d in pagination.items
        ]
        return {'documents': documents, 'total': pagination.total}

    @staticmethod
    def status() -> dict:
        info: dict[str, Any] = {}
        try:
            info = _knowledge_service().status()
        except Exception:  # noqa: BLE001
            info = {}
        docs = info.get('documents') or {}
        total = int(info.get('document_total') or 0)
        indexed = int(docs.get('READY') or 0)
        failed = int(docs.get('FAILED') or 0)
        return {
            'status': 'healthy' if info.get('ready') else 'degraded',
            'backend': RagService.backend_name(),
            'total_documents': total,
            'indexed_documents': indexed,
            'processing_documents': max(0, total - indexed - failed),
            'failed_documents': failed,
            'total_chunks': int(info.get('chunk_total') or 0),
            'embedded_chunks': int(info.get('chunk_embedded') or 0),
            'concept_total': int(info.get('concept_total') or 0),
            'vector': info.get('vector'),
            'last_sync': utc_now().isoformat(),
        }

    @staticmethod
    def build_context(question: str, *, user_id: int | None = None, top_k: int = 4) -> str:
        """给 LLM 的紧凑课程参考（不含分值）；证据不足返回空串。"""
        try:
            CourseSafetyService.ensure_safe(question)
        except Exception:  # noqa: BLE001
            return ''
        try:
            result = _knowledge_service().retrieve(question, user_id=user_id, top_k=top_k, log=False)
        except Exception:  # noqa: BLE001
            return ''
        if not result.get('knowledge_grounded'):
            return ''
        lines = []
        for item in result.get('reranked') or []:
            content = (item.get('content') or '').strip().replace('\n', ' ')
            if content:
                lines.append(f'- {content[:220]}')
        return '\n'.join(lines[:top_k])
