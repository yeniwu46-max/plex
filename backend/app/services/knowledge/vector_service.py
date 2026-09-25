# -*- coding: utf-8 -*-
"""VectorService：向量库的唯一入口（写入 / 删除 / 相似检索 / 状态）。

其他模块（Agent、路由、RAG）不得直接 import providers.vector_store。
"""
from __future__ import annotations

from typing import Any

from app.models import KnowledgeChunk

from .embedding_service import EmbeddingService
from .providers.vector_store import VectorHit, VectorRecord, VectorStore, get_vector_store


class VectorService:
    def __init__(self, store: VectorStore | None = None, embedding: EmbeddingService | None = None):
        self._store = store or get_vector_store()
        self._embedding = embedding or EmbeddingService()

    @property
    def store(self) -> VectorStore:
        return self._store

    @property
    def embedding(self) -> EmbeddingService:
        return self._embedding

    def describe(self) -> dict[str, Any]:
        info = self._store.describe()
        info['embedding'] = self._embedding.describe()
        return info

    # ------------------------------------------------------------------ write
    def index_chunks(self, chunks: list[KnowledgeChunk], concept_names: dict[str, str] | None = None) -> int:
        if not chunks:
            return 0
        concept_names = concept_names or {}
        texts = [
            EmbeddingService.build_chunk_text(
                chunk.title or '',
                chunk.content or '',
                [concept_names[c] for c in (chunk.concept_ids or []) if c in concept_names],
            )
            for chunk in chunks
        ]
        vectors = self._embedding.embed_chunks(texts)
        records = [
            VectorRecord(id=chunk.chunk_id, vector=vector, metadata=chunk.metadata_dict())
            for chunk, vector in zip(chunks, vectors)
        ]
        self._store.upsert(records)
        model = self._embedding.provider.identifier
        for chunk in chunks:
            chunk.embedding_status = 'READY'
            chunk.embedding_model = model
        return len(records)

    def remove_document(self, document_id: str) -> int:
        return self._store.delete_where({'document_id': document_id})

    def remove_chunks(self, chunk_ids: list[str]) -> None:
        self._store.delete(chunk_ids)

    # ------------------------------------------------------------------ read
    def search(self, query: str, top_k: int, where: dict[str, Any] | None = None) -> list[VectorHit]:
        vector = self._embedding.embed_query(query)
        return self._store.query(vector, top_k, where)

    def search_vector(self, vector: list[float], top_k: int, where: dict[str, Any] | None = None) -> list[VectorHit]:
        return self._store.query(vector, top_k, where)

    def count(self) -> int:
        return self._store.count()

    def has_vector(self, chunk_id: str) -> bool:
        return chunk_id in self._store.get([chunk_id])
