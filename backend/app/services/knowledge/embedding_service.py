# -*- coding: utf-8 -*-
"""EmbeddingService：批量向量化 + 查询向量化，屏蔽 Provider 差异。"""
from __future__ import annotations

from typing import Any

from .providers.embedding import EmbeddingError, EmbeddingProvider, get_embedding_provider
from .settings import retrieval_config


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider | None = None):
        self._provider = provider or get_embedding_provider()

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    def describe(self) -> dict[str, Any]:
        return self._provider.describe()

    def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        batch_size = int(retrieval_config().get('index', {}).get('embedding_batch_size', 32))
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            vectors.extend(self._provider.embed_texts(batch))
        if len(vectors) != len(texts):
            raise EmbeddingError('embedding count mismatch')
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._provider.embed_query(text)

    @staticmethod
    def build_chunk_text(title: str, content: str, concept_names: list[str] | None = None) -> str:
        """写入向量库的文本：标题 + 概念名 + 正文，提升概念级召回。"""
        parts = []
        if title:
            parts.append(title)
        if concept_names:
            parts.append('知识点：' + '、'.join(concept_names))
        parts.append(content or '')
        return '\n'.join(parts)
