# -*- coding: utf-8 -*-
"""LLMProvider 抽象：RAG 生成阶段与已有 LLM 供应商链解耦。

默认实现复用 ``agents.llm_client`` 的供应商解析（DeepSeek / OpenRouter / OpenAI / 星火，全部读环境变量），
以及 ``app.services.llm_stream.iter_openai_stream`` 的流式能力。测试环境自动禁外呼。
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator

from agents.http_client import direct_post
from app.services.model_observation import report_model
from agents.llm_client import _extract_json, llm_provider, messenger_provider, strip_asterisks


@dataclass
class LLMResult:
    text: str
    model: str | None = None
    provider: str | None = None
    token_usage: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    name = 'base'

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def generate(
        self,
        *,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
        max_tokens: int = 900,
        timeout: float = 18.0,
        temperature: float = 0.45,
    ) -> LLMResult | None: ...

    def generate_json(self, *, system: str, user: str, max_tokens: int = 400, timeout: float = 8.0) -> dict | None:
        result = self.generate(system=system, user=user, max_tokens=max_tokens, timeout=timeout, temperature=0.1)
        return _extract_json(result.text) if result else None

    def stream(
        self,
        *,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
        max_tokens: int = 900,
    ) -> Iterator[str] | None:
        return None


def _provider_label(endpoint: str) -> str:
    endpoint = endpoint or ''
    if 'deepseek' in endpoint:
        return 'deepseek'
    if 'openrouter' in endpoint:
        return 'openrouter'
    if 'xf-yun' in endpoint or 'spark' in endpoint:
        return 'spark'
    if 'openai' in endpoint:
        return 'openai'
    return 'openai-compatible'


class OpenAICompatibleLLMProvider(LLMProvider):
    """基于 (api_key, endpoint, model) 三元组的 OpenAI 兼容 chat/completions 调用。"""

    name = 'openai-compatible'

    def __init__(self, purpose: str = 'rag'):
        self._purpose = purpose

    def _resolve(self) -> tuple[str, str, str] | None:
        choice = os.getenv('RAG_LLM_PROVIDER', '').strip().lower()
        if choice == 'messenger':
            return messenger_provider() or llm_provider()
        if choice == 'default':
            return llm_provider()
        # 默认：小E 驿站通道优先（与学生端对话保持同一模型），再回落到通用链
        return messenger_provider() or llm_provider()

    def available(self) -> bool:
        return self._resolve() is not None

    def _messages(self, system: str, user: str, history: list[dict[str, str]] | None) -> list[dict[str, str]]:
        messages = [{'role': 'system', 'content': system}]
        for row in history or []:
            role = str(row.get('role') or '').strip()
            content = str(row.get('content') or '').strip()
            if role in {'user', 'assistant'} and content:
                messages.append({'role': role, 'content': content})
        messages.append({'role': 'user', 'content': user})
        return messages

    def generate(
        self,
        *,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
        max_tokens: int = 900,
        timeout: float = 18.0,
        temperature: float = 0.45,
        preserve_text: bool = False,
    ) -> LLMResult | None:
        provider = self._resolve()
        if not provider:
            return None
        api_key, endpoint, model = provider
        try:
            resp = direct_post(
                endpoint,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': model,
                    'messages': self._messages(system, user, history),
                    'max_tokens': max_tokens,
                    'temperature': temperature,
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            usage = data.get('usage') or {}
        except Exception as exc:  # Transport metadata only; no URL, header or body logging.
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            error = f'http_{status}' if type(status) is int else 'transport_or_response_error'
            report_model(status='failed', provider=_provider_label(endpoint), model=model, error_code=error, token_usage={})
            return None
        # Structured code must retain multiplication operators and exact source.
        text = str(content or '').strip() if preserve_text or self._purpose == 'structured_code' else strip_asterisks(str(content or ''))
        if not text:
            report_model(status='failed', provider=_provider_label(endpoint), model=model, error_code='empty_response', token_usage=usage)
            return None
        report_model(status='succeeded', provider=_provider_label(endpoint), model=model, error_code=None, token_usage=usage)
        return LLMResult(
            text=text,
            model=model,
            provider=_provider_label(endpoint),
            token_usage={
                'prompt_tokens': usage.get('prompt_tokens'),
                'completion_tokens': usage.get('completion_tokens'),
                'total_tokens': usage.get('total_tokens'),
            },
        )

    def generate_json(self, *, system: str, user: str, max_tokens: int = 400, timeout: float = 8.0) -> dict | None:
        # JSON values may contain multiplication and Markdown punctuation as data.
        # Formatting cleanup belongs to the renderer, never the model contract.
        result = self.generate(system=system, user=user, max_tokens=max_tokens,
                               timeout=timeout, temperature=0.1, preserve_text=True)
        return _extract_json(result.text) if result else None

    def stream(
        self,
        *,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
        max_tokens: int = 900,
    ) -> Iterator[str] | None:
        from app.services.llm_stream import iter_openai_stream

        provider = self._resolve()
        if not provider:
            return None
        return iter_openai_stream(provider, self._messages(system, user, history), max_tokens=max_tokens)

    def describe(self) -> dict[str, Any]:
        provider = self._resolve()
        if not provider:
            return {'available': False}
        _key, endpoint, model = provider
        return {'available': True, 'provider': _provider_label(endpoint), 'model': model}


_DEFAULT: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = OpenAICompatibleLLMProvider()
    return _DEFAULT
