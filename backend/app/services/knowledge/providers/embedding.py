# -*- coding: utf-8 -*-
"""EmbeddingProvider 抽象与实现。

- OpenAICompatibleEmbeddingProvider：调用 OpenAI 兼容 ``/embeddings`` 接口（OpenAI、阿里云百炼、
  SiliconFlow、Ollama 等），Key/端点/模型全部来自环境变量。
- LocalHashEmbeddingProvider：零依赖、确定性的字符 n-gram 哈希投影，作为无外网/未配置 Key 时的
  真实（非 Mock）回退：向量可比较、可持久化、单测稳定。配合词法 BM25 形成 Hybrid 检索。
"""
from __future__ import annotations

import hashlib
import math
import threading
from abc import ABC, abstractmethod
from typing import Iterable

from ..settings import embedding_env
from ..text_utils import normalize_text, tokenize


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    name: str = 'base'
    model: str = ''
    dimensions: int = 0
    # 余弦相似度的绝对值是否可用于置信度判断（哈希投影向量只适合排序，不适合绝对阈值）
    absolute_similarity_reliable: bool = True

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def describe(self) -> dict:
        return {'provider': self.name, 'model': self.model, 'dimensions': self.dimensions}

    @property
    def identifier(self) -> str:
        return f'{self.name}:{self.model}'


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """字符 n-gram / 词 token 的哈希投影向量（signed hashing trick），L2 归一化。"""

    name = 'local-hash'
    absolute_similarity_reliable = False

    def __init__(self, dimensions: int = 512):
        self.dimensions = max(64, int(dimensions))
        self.model = f'ngram-hash-{self.dimensions}'

    def _features(self, text: str) -> Iterable[str]:
        text = normalize_text(text).lower()
        for token in tokenize(text, bigrams=True, drop_stopwords=True):
            yield f't:{token}'
        compact = text.replace(' ', '')
        for n in (3,):
            for i in range(max(0, len(compact) - n + 1)):
                yield f'g{n}:{compact[i:i + n]}'

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        count = 0
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode('utf-8'), digest_size=8).digest()
            index = int.from_bytes(digest[:4], 'little') % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            # token 特征权重高于字符 3-gram
            weight = 1.0 if feature.startswith('t:') else 0.5
            vector[index] += sign * weight
            count += 1
        if count == 0:
            return vector
        return _l2_normalize(vector)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text or '') for text in texts]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    name = 'openai-compatible'

    def __init__(self, api_key: str, base_url: str, model: str, dimensions: int | None = None, timeout: float = 20.0):
        if not api_key:
            raise EmbeddingError('embedding api key missing')
        self._api_key = api_key
        self._endpoint = f'{base_url.rstrip("/")}/embeddings'
        self.model = model
        self.dimensions = int(dimensions or 0)
        self._timeout = timeout
        self._lock = threading.Lock()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        from agents.http_client import direct_post

        if not texts:
            return []
        payload: dict = {'model': self.model, 'input': [t if t else ' ' for t in texts]}
        if self.dimensions:
            payload['dimensions'] = self.dimensions
        try:
            resp = direct_post(
                self._endpoint,
                headers={'Authorization': f'Bearer {self._api_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(f'embedding request failed: {exc}') from exc
        rows = sorted(data.get('data') or [], key=lambda item: item.get('index', 0))
        vectors = [list(map(float, row.get('embedding') or [])) for row in rows]
        if len(vectors) != len(texts):
            raise EmbeddingError('embedding response size mismatch')
        if vectors and not self.dimensions:
            self.dimensions = len(vectors[0])
        return [_l2_normalize(v) for v in vectors]


_PROVIDER_LOCK = threading.Lock()
_PROVIDER: EmbeddingProvider | None = None
_PROVIDER_KEY: tuple | None = None


def _blocked_in_tests() -> bool:
    """测试环境默认禁止外呼（与 agents.llm_client 的 LLM_ALLOW_IN_TESTS 约定一致）。"""
    try:
        from flask import current_app, has_app_context
    except ImportError:
        return False
    return bool(has_app_context() and current_app.config.get('TESTING') and not current_app.config.get('LLM_ALLOW_IN_TESTS'))


def build_embedding_provider() -> EmbeddingProvider:
    env = embedding_env()
    choice = env['provider']
    local_dims = int(env['local_dimensions'] or 512)
    if choice == 'local' or _blocked_in_tests():
        return LocalHashEmbeddingProvider(local_dims)
    if choice in {'openai', 'openai-compatible'} or (not choice and env['api_key']):
        if not env['api_key']:
            raise EmbeddingError('EMBEDDING_PROVIDER=openai 但未配置 EMBEDDING_API_KEY / OPENAI_API_KEY')
        dims = int(env['dimensions']) if env['dimensions'].isdigit() else None
        return OpenAICompatibleEmbeddingProvider(
            env['api_key'], env['base_url'], env['model'], dims, float(env['timeout'] or 20)
        )
    return LocalHashEmbeddingProvider(local_dims)


def get_embedding_provider() -> EmbeddingProvider:
    global _PROVIDER, _PROVIDER_KEY
    env = embedding_env()
    key = (_blocked_in_tests(), env['provider'], env['model'], bool(env['api_key']))
    with _PROVIDER_LOCK:
        if _PROVIDER is None or _PROVIDER_KEY != key:
            _PROVIDER = build_embedding_provider()
            _PROVIDER_KEY = key
        return _PROVIDER


def reset_embedding_provider() -> None:
    global _PROVIDER, _PROVIDER_KEY
    with _PROVIDER_LOCK:
        _PROVIDER = None
        _PROVIDER_KEY = None


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(-1.0, min(1.0, dot / (na * nb)))
