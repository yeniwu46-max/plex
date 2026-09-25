# -*- coding: utf-8 -*-
"""RAG 请求日志：用于 Debug、教师端高频问题统计、学习行为证据。

隐私约束：不存储完整原始 query，仅存脱敏后的预览（长度受配置限制）与哈希。
"""
from __future__ import annotations

from app.utils.time import utc_now

from .base import db


class RagQueryLog(db.Model):
    __tablename__ = 'rag_query_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True)
    role = db.Column(db.String(16))
    scene = db.Column(db.String(32), default='chat', index=True)  # chat|trial|debug|agent|retrieve
    query_hash = db.Column(db.String(64), index=True)
    query_preview = db.Column(db.String(200))
    intent = db.Column(db.String(32))
    detected_concepts = db.Column(db.JSON)
    graph_nodes = db.Column(db.JSON)
    retrieved_chunks = db.Column(db.JSON)
    retrieval_scores = db.Column(db.JSON)
    rerank_scores = db.Column(db.JSON)
    teaching_strategy = db.Column(db.JSON)
    hint_level = db.Column(db.Integer)
    model = db.Column(db.String(80))
    provider = db.Column(db.String(40))
    generation_mode = db.Column(db.String(24))  # llm|extractive|refused
    latency_ms = db.Column(db.Integer)
    token_usage = db.Column(db.JSON)
    confidence = db.Column(db.Float)
    confidence_level = db.Column(db.String(16))
    knowledge_grounded = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(16), nullable=False, default='ok')  # ok|low_confidence|blocked|error
    error_message = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role': self.role,
            'scene': self.scene,
            'query_hash': self.query_hash,
            'query_preview': self.query_preview,
            'intent': self.intent,
            'detected_concepts': list(self.detected_concepts or []),
            'graph_nodes': list(self.graph_nodes or []),
            'retrieved_chunks': list(self.retrieved_chunks or []),
            'retrieval_scores': self.retrieval_scores or {},
            'rerank_scores': self.rerank_scores or {},
            'teaching_strategy': list(self.teaching_strategy or []),
            'hint_level': self.hint_level,
            'model': self.model,
            'provider': self.provider,
            'generation_mode': self.generation_mode,
            'latency_ms': self.latency_ms,
            'token_usage': self.token_usage or {},
            'confidence': self.confidence,
            'confidence_level': self.confidence_level,
            'knowledge_grounded': bool(self.knowledge_grounded),
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
