# -*- coding: utf-8 -*-
"""内存 BM25 词法索引：与向量检索组成 Hybrid Retrieval。

索引数据来自 MySQL 的 active chunk（正文 + 标题），以 (chunk 数, 最新 updated_at) 作为版本号懒重建。
"""
from __future__ import annotations

import math
import threading
from collections import Counter, defaultdict
from typing import Any

from app.models import KnowledgeChunk, db

from .text_utils import tokenize

_K1 = 1.5
_B = 0.75


class _Bm25Index:
    def __init__(self, docs: list[tuple[str, dict[str, Any], list[str]]]):
        self.ids: list[str] = []
        self.metas: list[dict[str, Any]] = []
        self.tf: list[Counter] = []
        self.doc_len: list[int] = []
        self.df: Counter = Counter()
        for chunk_id, meta, tokens in docs:
            counts = Counter(tokens)
            self.ids.append(chunk_id)
            self.metas.append(meta)
            self.tf.append(counts)
            self.doc_len.append(len(tokens))
            self.df.update(counts.keys())
        self.n = len(self.ids)
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        self.postings: dict[str, list[int]] = defaultdict(list)
        for index, counts in enumerate(self.tf):
            for term in counts:
                self.postings[term].append(index)

    def search(self, query: str, top_k: int, where: dict[str, Any] | None = None) -> list[tuple[str, float, dict]]:
        if not self.n:
            return []
        terms = tokenize(query)
        if not terms:
            return []
        scores: dict[int, float] = defaultdict(float)
        covered: dict[int, float] = defaultdict(float)
        unique_terms = set(terms)
        idf_of: dict[str, float] = {}
        for term in unique_terms:
            df = self.df.get(term)
            # 未出现于语料的词按最大 idf 计入分母（它们是“查询中未被覆盖的信息”）
            idf_of[term] = math.log(1 + (self.n - (df or 0) + 0.5) / ((df or 0) + 0.5))
            if not df:
                continue
            idf = idf_of[term]
            for index in self.postings[term]:
                tf = self.tf[index][term]
                denom = tf + _K1 * (1 - _B + _B * self.doc_len[index] / (self.avgdl or 1))
                scores[index] += idf * tf * (_K1 + 1) / denom
                covered[index] += idf
        total_idf = sum(idf_of.values()) or 1.0
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        out: list[tuple[str, float, dict]] = []
        max_score = ranked[0][1] if ranked else 1.0
        for index, score in ranked:
            meta = self.metas[index]
            if where and not _match(meta, where):
                continue
            meta = dict(meta)
            meta['_bm25_raw'] = round(score, 4)
            # 绝对证据：查询信息量（idf 加权）被该 chunk 覆盖的比例，可跨查询比较
            meta['_bm25_abs'] = round(min(1.0, covered[index] / total_idf), 4)
            out.append((self.ids[index], score / (max_score or 1.0), meta))
            if len(out) >= top_k:
                break
        return out


    def coverage(self, query: str, chunk_ids: list[str]) -> dict[str, float]:
        """给定 chunk 的查询覆盖率（idf 加权），用于为非词法通道召回的候选补充绝对证据。"""
        terms = set(tokenize(query))
        if not terms or not self.n:
            return {cid: 0.0 for cid in chunk_ids}
        idf_of = {t: math.log(1 + (self.n - self.df.get(t, 0) + 0.5) / (self.df.get(t, 0) + 0.5)) for t in terms}
        total = sum(idf_of.values()) or 1.0
        index_of = {cid: i for i, cid in enumerate(self.ids)}
        out: dict[str, float] = {}
        for cid in chunk_ids:
            pos = index_of.get(cid)
            if pos is None:
                out[cid] = 0.0
                continue
            counts = self.tf[pos]
            out[cid] = round(min(1.0, sum(idf for t, idf in idf_of.items() if t in counts) / total), 4)
        return out


def _match(meta: dict[str, Any], where: dict[str, Any]) -> bool:
    for key, cond in where.items():
        value = meta.get(key)
        if isinstance(cond, dict):
            if '$in' in cond and value not in cond['$in']:
                return False
            if '$contains' in cond and cond['$contains'] not in (value or []):
                return False
        elif value != cond:
            return False
    return True


class LexicalIndex:
    _lock = threading.RLock()
    _index: _Bm25Index | None = None
    _version: tuple | None = None

    @classmethod
    def invalidate(cls) -> None:
        with cls._lock:
            cls._index = None
            cls._version = None

    @classmethod
    def _current_version(cls) -> tuple:
        row = db.session.query(
            db.func.count(KnowledgeChunk.chunk_id), db.func.max(KnowledgeChunk.updated_at)
        ).filter(KnowledgeChunk.status == 'active').first()
        return (int(row[0] or 0), str(row[1] or ''))

    @classmethod
    def get(cls) -> _Bm25Index:
        version = cls._current_version()
        with cls._lock:
            if cls._index is None or cls._version != version:
                cls._index = cls._build()
                cls._version = version
            return cls._index

    @staticmethod
    def _build() -> _Bm25Index:
        docs = []
        rows = KnowledgeChunk.query.filter(KnowledgeChunk.status == 'active').all()
        for row in rows:
            tokens = tokenize(f'{row.title or ""}\n{row.content or ""}')
            meta = {
                'chunk_id': row.chunk_id,
                'document_id': row.document_id,
                'course_id': row.course_id,
                'knowledge_type': row.knowledge_type,
                'concept_ids': list(row.concept_ids or []),
                'teacher_verified': bool(row.teacher_verified),
                'difficulty': row.difficulty,
            }
            docs.append((row.chunk_id, meta, tokens))
        return _Bm25Index(docs)

    @classmethod
    def search(cls, query: str, top_k: int, where: dict[str, Any] | None = None) -> list[tuple[str, float, dict]]:
        return cls.get().search(query, top_k, where)

    @classmethod
    def coverage(cls, query: str, chunk_ids: list[str]) -> dict[str, float]:
        return cls.get().coverage(query, chunk_ids)
