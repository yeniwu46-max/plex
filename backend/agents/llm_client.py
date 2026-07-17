# -*- coding: utf-8 -*-
"""OpenAI 兼容 LLM 客户端 — 供智能体流水线增强反馈与诊断。"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import requests


def llm_provider() -> tuple[str, str, str] | None:
    """返回 (api_key, endpoint, model)，优先 DeepSeek，其次 OpenRouter。"""
    deepseek = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if deepseek:
        base = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1').rstrip('/')
        return (
            deepseek,
            f'{base}/chat/completions',
            os.getenv('DEEPSEEK_MODEL', 'deepseek-chat'),
        )
    openrouter = os.getenv('OPENROUTER_API_KEY', '').strip()
    if openrouter:
        return (
            openrouter,
            'https://openrouter.ai/api/v1/chat/completions',
            os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
        )
    openai_key = os.getenv('OPENAI_API_KEY', '').strip()
    if openai_key:
        base = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        return (
            openai_key,
            f'{base}/chat/completions',
            os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        )
    return None


def api_key_configured() -> bool:
    return llm_provider() is not None


def _extract_json(text: str) -> dict[str, Any] | None:
    text = (text or '').strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def chat_json(
    *,
    system: str,
    user: str,
    timeout: float = 45.0,
    max_tokens: int = 640,
) -> dict[str, Any] | None:
    """调用 LLM 并解析 JSON 对象响应。"""
    provider = llm_provider()
    if not provider:
        return None
    api_key, endpoint, model = provider
    try:
        resp = requests.post(
            endpoint,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'max_tokens': max_tokens,
                'temperature': 0.4,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content']
        return _extract_json(content)
    except Exception:
        return None


def chat_text(
    *,
    system: str,
    user: str,
    history: list[dict[str, str]] | None = None,
    timeout: float = 45.0,
    max_tokens: int = 900,
) -> str | None:
    """调用 LLM 并返回纯文本回复。"""
    provider = llm_provider()
    if not provider:
        return None
    api_key, endpoint, model = provider
    messages: list[dict[str, str]] = [{'role': 'system', 'content': system}]
    for row in history or []:
        role = str(row.get('role') or '').strip()
        content = str(row.get('content') or '').strip()
        if role in {'user', 'assistant'} and content:
            messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': user})
    try:
        resp = requests.post(
            endpoint,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': 0.55,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content']
        return str(content or '').strip() or None
    except Exception:
        return None
