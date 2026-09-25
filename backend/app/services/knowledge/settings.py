# -*- coding: utf-8 -*-
"""Knowledge Intelligence Layer 配置加载。

- 权重、阈值、Prompt 全部来自 ``config/*.json``，不写死在代码里。
- ``KNOWLEDGE_CONFIG_DIR`` 环境变量可指向一个覆盖目录（同名 json 会做浅层合并）。
- API Key / 端点等敏感信息只从环境变量读取（.env），不进入配置文件与源码。
"""
from __future__ import annotations

import copy
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG_DIR = Path(__file__).resolve().parent / 'config'


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


@lru_cache(maxsize=8)
def load_config(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / f'{name}.json'
    data: dict[str, Any] = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding='utf-8'))
    override_dir = os.getenv('KNOWLEDGE_CONFIG_DIR', '').strip()
    if override_dir:
        override_path = Path(override_dir) / f'{name}.json'
        if override_path.is_file():
            data = _deep_merge(data, json.loads(override_path.read_text(encoding='utf-8')))
    data.pop('$comment', None)
    return data


def retrieval_config() -> dict[str, Any]:
    return load_config('retrieval')


def strategy_config() -> dict[str, Any]:
    return load_config('strategy')


def prompts_config() -> dict[str, Any]:
    return load_config('prompts')


def reload_configs() -> None:
    load_config.cache_clear()


# ---------------------------------------------------------------------------
# 环境变量（敏感信息 / 部署相关），不进 json
# ---------------------------------------------------------------------------

def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, '').strip().lower()
    if not raw:
        return default
    return raw in {'1', 'true', 'yes', 'on'}


def embedding_env() -> dict[str, str]:
    """Embedding Provider 环境配置。

    - EMBEDDING_PROVIDER: openai | local（默认自动：有 key 用 openai 兼容，否则 local）
    - EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL：OpenAI 兼容 embeddings 接口
      （兼容 OpenAI、阿里云百炼、SiliconFlow、Ollama 等），未设置 key 时回退 OPENAI_API_KEY。
    - EMBEDDING_DIMENSIONS：可选，部分服务支持指定维度。
    """
    return {
        'provider': os.getenv('EMBEDDING_PROVIDER', '').strip().lower(),
        'api_key': os.getenv('EMBEDDING_API_KEY', '').strip() or os.getenv('OPENAI_API_KEY', '').strip(),
        'base_url': (
            os.getenv('EMBEDDING_BASE_URL', '').strip()
            or os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').strip()
        ).rstrip('/'),
        'model': os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small').strip(),
        'dimensions': os.getenv('EMBEDDING_DIMENSIONS', '').strip(),
        'local_dimensions': os.getenv('EMBEDDING_LOCAL_DIMENSIONS', '512').strip(),
        'timeout': os.getenv('EMBEDDING_TIMEOUT_SECONDS', '20').strip(),
    }


def vector_env() -> dict[str, str]:
    """VectorStore 环境配置。

    - VECTOR_BACKEND: chroma | local（默认自动：chromadb 可导入则 chroma，否则 local）
    - VECTOR_STORE_PATH: 持久化目录（默认 instance/vector_store）
    - VECTOR_COLLECTION: 集合名（默认 plex_knowledge）
    """
    return {
        'backend': os.getenv('VECTOR_BACKEND', '').strip().lower(),
        'path': os.getenv('VECTOR_STORE_PATH', '').strip(),
        'collection': os.getenv('VECTOR_COLLECTION', 'plex_knowledge').strip() or 'plex_knowledge',
    }


def knowledge_env() -> dict[str, Any]:
    return {
        'index_sync': env_flag('KNOWLEDGE_INDEX_SYNC', False),
        'auto_bootstrap': env_flag('KNOWLEDGE_AUTO_BOOTSTRAP', True),
        'auto_seed': env_flag('KNOWLEDGE_AUTO_SEED', True),
        'auto_index_builtin': env_flag('KNOWLEDGE_AUTO_INDEX_BUILTIN', True),
        'rag_llm_enabled': env_flag('RAG_LLM_ENABLED', True),
        'rag_llm_timeout': float(os.getenv('RAG_LLM_TIMEOUT_SECONDS', '18') or 18),
        'rag_llm_max_tokens': int(os.getenv('RAG_LLM_MAX_TOKENS', '900') or 900),
    }
