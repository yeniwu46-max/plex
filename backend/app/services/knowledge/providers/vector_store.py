# -*- coding: utf-8 -*-
"""VectorStore 抽象：只存 embedding + chunk_id + 检索 metadata，正文与业务字段在 MySQL。

实现：
- ChromaVectorStore：chromadb PersistentClient（本地目录，Windows 友好，可换 HttpClient 指向 Docker 服务）。
- LocalVectorStore：零依赖 JSON 持久化 + 余弦检索（numpy 可选加速），也用于测试（内存模式）。

Agent / 路由不得直接使用本模块，统一经 VectorService。
"""
from __future__ import annotations

import json
import math
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..settings import vector_env

try:  # numpy 为可选加速
    import numpy as _np
except Exception:  # noqa: BLE001
    _np = None


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorHit:
    id: str
    score: float  # 余弦相似度 0..1（已从距离转换）
    metadata: dict[str, Any] = field(default_factory=dict)


_SCALAR_TYPES = (str, int, float, bool)


def flatten_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """向量库 metadata 仅允许标量；列表转为 ``|a|b|`` 字符串以便包含匹配。"""
    flat: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        if isinstance(value, _SCALAR_TYPES):
            flat[key] = value
        elif isinstance(value, (list, tuple, set)):
            flat[key] = '|' + '|'.join(str(v) for v in value) + '|' if value else '||'
        else:
            flat[key] = json.dumps(value, ensure_ascii=False)
    return flat


def _as_list(value: Any) -> list:
    """chroma 结果字段可能是 list / numpy 数组 / None，统一为 list（避免对数组做布尔判断）。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except TypeError:
        return []


def _first_row(value: Any) -> list:
    rows = _as_list(value)
    return _as_list(rows[0]) if rows else []


def match_where(metadata: dict[str, Any], where: dict[str, Any] | None) -> bool:
    """统一的简单过滤语义：{key: value} 等值；{key: {'$in': [...]}}；{key: {'$contains': 'x'}}。"""
    if not where:
        return True
    for key, cond in where.items():
        value = metadata.get(key)
        if isinstance(cond, dict):
            if '$in' in cond and value not in cond['$in']:
                return False
            if '$contains' in cond:
                haystack = value if isinstance(value, str) else ''
                if f'|{cond["$contains"]}|' not in haystack:
                    return False
            if '$eq' in cond and value != cond['$eq']:
                return False
        elif value != cond:
            return False
    return True


class VectorStore(ABC):
    backend: str = 'base'

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    def delete(self, ids: list[str]) -> None: ...

    @abstractmethod
    def delete_where(self, where: dict[str, Any]) -> int: ...

    @abstractmethod
    def query(self, vector: list[float], top_k: int, where: dict[str, Any] | None = None) -> list[VectorHit]: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def get(self, ids: list[str]) -> dict[str, VectorRecord]: ...

    def existing_ids(self, ids: list[str]) -> set[str]:
        """返回 ids 中已有向量的子集（用于一致性校验）。子类可覆盖为更省的实现。"""
        return set(self.get(ids).keys())

    def describe(self) -> dict[str, Any]:
        return {'backend': self.backend, 'count': self.count()}


# ---------------------------------------------------------------------------
# Local JSON / in-memory implementation
# ---------------------------------------------------------------------------

class LocalVectorStore(VectorStore):
    backend = 'local'

    def __init__(self, path: Path | None, collection: str):
        self._path = (path / f'{collection}.json') if path else None
        self._lock = threading.RLock()
        self._ids: list[str] = []
        self._vectors: list[list[float]] = []
        self._metas: list[dict[str, Any]] = []
        self._index: dict[str, int] = {}
        self._matrix = None
        self._load()

    # -- persistence -------------------------------------------------------
    def _load(self) -> None:
        if not self._path or not self._path.is_file():
            return
        try:
            data = json.loads(self._path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return
        self._ids = list(data.get('ids') or [])
        self._vectors = [list(map(float, v)) for v in data.get('vectors') or []]
        self._metas = list(data.get('metadatas') or [])
        self._rebuild_index()

    def _flush(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix('.tmp')
        tmp.write_text(
            json.dumps({'ids': self._ids, 'vectors': self._vectors, 'metadatas': self._metas}, ensure_ascii=False),
            encoding='utf-8',
        )
        os.replace(tmp, self._path)

    def _rebuild_index(self) -> None:
        self._index = {vid: i for i, vid in enumerate(self._ids)}
        self._matrix = _np.array(self._vectors, dtype='float32') if (_np is not None and self._vectors) else None

    # -- api ---------------------------------------------------------------
    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            for rec in records:
                meta = flatten_metadata(rec.metadata)
                pos = self._index.get(rec.id)
                if pos is None:
                    self._index[rec.id] = len(self._ids)
                    self._ids.append(rec.id)
                    self._vectors.append(list(map(float, rec.vector)))
                    self._metas.append(meta)
                else:
                    self._vectors[pos] = list(map(float, rec.vector))
                    self._metas[pos] = meta
            self._rebuild_index()
            self._flush()

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        with self._lock:
            drop = set(ids)
            keep = [i for i, vid in enumerate(self._ids) if vid not in drop]
            self._ids = [self._ids[i] for i in keep]
            self._vectors = [self._vectors[i] for i in keep]
            self._metas = [self._metas[i] for i in keep]
            self._rebuild_index()
            self._flush()

    def delete_where(self, where: dict[str, Any]) -> int:
        with self._lock:
            victims = [vid for vid, meta in zip(self._ids, self._metas) if match_where(meta, where)]
        self.delete(victims)
        return len(victims)

    def get(self, ids: list[str]) -> dict[str, VectorRecord]:
        with self._lock:
            out = {}
            for vid in ids:
                pos = self._index.get(vid)
                if pos is not None:
                    out[vid] = VectorRecord(vid, list(self._vectors[pos]), dict(self._metas[pos]))
            return out

    def existing_ids(self, ids: list[str]) -> set[str]:
        with self._lock:
            return {vid for vid in ids if vid in self._index}

    def query(self, vector: list[float], top_k: int, where: dict[str, Any] | None = None) -> list[VectorHit]:
        with self._lock:
            if not self._ids:
                return []
            if self._matrix is not None:
                q = _np.array(vector, dtype='float32')
                qn = float(_np.linalg.norm(q)) or 1.0
                norms = _np.linalg.norm(self._matrix, axis=1)
                norms[norms == 0] = 1.0
                sims = (self._matrix @ q) / (norms * qn)
                order = _np.argsort(-sims)
                scored = [(int(i), float(sims[i])) for i in order]
            else:
                qn = math.sqrt(sum(x * x for x in vector)) or 1.0
                scored = []
                for i, vec in enumerate(self._vectors):
                    dn = math.sqrt(sum(x * x for x in vec)) or 1.0
                    dot = sum(x * y for x, y in zip(vec, vector))
                    scored.append((i, dot / (dn * qn)))
                scored.sort(key=lambda item: -item[1])
            hits: list[VectorHit] = []
            for i, sim in scored:
                meta = self._metas[i]
                if not match_where(meta, where):
                    continue
                hits.append(VectorHit(self._ids[i], max(0.0, (sim + 1) / 2 if sim < 0 else sim), dict(meta)))
                if len(hits) >= top_k:
                    break
            return hits

    def count(self) -> int:
        return len(self._ids)


# ---------------------------------------------------------------------------
# Chroma implementation
# ---------------------------------------------------------------------------

class ChromaVectorStore(VectorStore):
    backend = 'chroma'

    def __init__(self, path: Path, collection: str):
        import chromadb  # 延迟导入，未安装时由工厂回退

        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path))
        self._collection = self._client.get_or_create_collection(
            name=collection, metadata={'hnsw:space': 'cosine'}
        )
        self._lock = threading.RLock()

    @staticmethod
    def _chroma_where(where: dict[str, Any] | None) -> tuple[dict | None, dict[str, Any]]:
        """Chroma 不支持 $contains（metadata），拆成原生 where 与 Python 后过滤两部分。"""
        if not where:
            return None, {}
        native: list[dict] = []
        post: dict[str, Any] = {}
        for key, cond in where.items():
            if isinstance(cond, dict):
                if '$in' in cond:
                    native.append({key: {'$in': list(cond['$in'])}})
                elif '$eq' in cond:
                    native.append({key: {'$eq': cond['$eq']}})
                else:
                    post[key] = cond
            else:
                native.append({key: {'$eq': cond}})
        if not native:
            return None, post
        if len(native) == 1:
            return native[0], post
        return {'$and': native}, post

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            self._collection.upsert(
                ids=[r.id for r in records],
                embeddings=[list(map(float, r.vector)) for r in records],
                metadatas=[flatten_metadata(r.metadata) or {'_': 1} for r in records],
            )

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        with self._lock:
            self._collection.delete(ids=list(ids))

    def delete_where(self, where: dict[str, Any]) -> int:
        native, post = self._chroma_where(where)
        with self._lock:
            got = self._collection.get(where=native, include=['metadatas']) if native else self._collection.get(include=['metadatas'])
            ids = [
                vid for vid, meta in zip(_as_list(got.get('ids')), _as_list(got.get('metadatas')))
                if match_where(meta or {}, post)
            ]
            if ids:
                self._collection.delete(ids=ids)
            return len(ids)

    def get(self, ids: list[str]) -> dict[str, VectorRecord]:
        if not ids:
            return {}
        with self._lock:
            got = self._collection.get(ids=list(ids), include=['embeddings', 'metadatas'])
        out = {}
        ids_got = _as_list(got.get('ids'))
        embs = _as_list(got.get('embeddings'))  # chroma 可能返回 numpy 数组，不能用 `or []`
        metas = _as_list(got.get('metadatas'))
        for idx, vid in enumerate(ids_got):
            emb = embs[idx] if idx < len(embs) else None
            if emb is None:
                continue
            meta = metas[idx] if idx < len(metas) else None
            out[vid] = VectorRecord(vid, [float(x) for x in emb], dict(meta or {}))
        return out

    def existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        with self._lock:
            got = self._collection.get(ids=list(ids), include=[])
        return set(_as_list(got.get('ids')))

    def query(self, vector: list[float], top_k: int, where: dict[str, Any] | None = None) -> list[VectorHit]:
        native, post = self._chroma_where(where)
        with self._lock:
            total = self._collection.count()
            if total == 0:
                return []
            n = min(total, top_k * (3 if post else 1))
            result = self._collection.query(
                query_embeddings=[list(map(float, vector))],
                n_results=max(1, n),
                where=native,
                include=['metadatas', 'distances'],
            )
        ids = _first_row(result.get('ids'))
        metas = _first_row(result.get('metadatas'))
        dists = _first_row(result.get('distances'))
        hits: list[VectorHit] = []
        for vid, meta, dist in zip(ids, metas, dists):
            meta = dict(meta or {})
            if not match_where(meta, post):
                continue
            sim = 1.0 - float(dist or 0.0)  # cosine distance -> similarity
            hits.append(VectorHit(vid, max(0.0, min(1.0, sim)), meta))
            if len(hits) >= top_k:
                break
        return hits

    def count(self) -> int:
        with self._lock:
            return int(self._collection.count())


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_STORE_LOCK = threading.Lock()
_STORE: VectorStore | None = None
_STORE_KEY: tuple | None = None


def _resolve_path(app_instance_path: str | None) -> Path:
    env = vector_env()
    if env['path']:
        return Path(env['path'])
    base = Path(app_instance_path) if app_instance_path else Path('instance')
    return base / 'vector_store'


def build_vector_store(*, testing: bool = False, instance_path: str | None = None) -> VectorStore:
    env = vector_env()
    collection = env['collection']
    backend = env['backend']
    if testing and backend not in {'chroma', 'local'}:
        return LocalVectorStore(None, collection)
    if backend == 'memory':
        return LocalVectorStore(None, collection)
    path = _resolve_path(instance_path)
    if backend == 'local':
        return LocalVectorStore(path, collection)
    if backend in {'', 'chroma'}:
        try:
            return ChromaVectorStore(path / 'chroma', collection)
        except Exception:  # noqa: BLE001 - chromadb 不可用则回退本地实现
            if backend == 'chroma':
                raise
    return LocalVectorStore(path, collection)


def get_vector_store() -> VectorStore:
    """按当前 Flask app 配置返回单例 VectorStore。"""
    global _STORE, _STORE_KEY
    from flask import current_app, has_app_context

    testing = False
    instance_path = None
    if has_app_context():
        testing = bool(current_app.config.get('TESTING'))
        instance_path = current_app.instance_path
    key = (testing, instance_path, vector_env()['backend'], vector_env()['collection'])
    with _STORE_LOCK:
        if _STORE is None or _STORE_KEY != key:
            _STORE = build_vector_store(testing=testing, instance_path=instance_path)
            _STORE_KEY = key
        return _STORE


def reset_vector_store() -> None:
    global _STORE, _STORE_KEY
    with _STORE_LOCK:
        _STORE = None
        _STORE_KEY = None
