# -*- coding: utf-8 -*-
"""OpenAI 兼容 LLM 客户端 — 供智能体流水线增强反馈与诊断。"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from agents.http_client import direct_post


def _blocked_in_tests() -> bool:
    """测试环境默认禁用真实 LLM 外呼（与 Spark 的 SPARK_ALLOW_IN_TESTS 约定一致）。"""
    try:
        from flask import current_app, has_app_context
    except ImportError:
        return False
    return bool(
        has_app_context()
        and current_app.config.get('TESTING')
        and not current_app.config.get('LLM_ALLOW_IN_TESTS')
    )


def _deepseek_tuple(api_key: str) -> tuple[str, str, str]:
    base = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1').rstrip('/')
    return (
        api_key,
        f'{base}/chat/completions',
        os.getenv('DEEPSEEK_MODEL', 'deepseek-chat'),
    )


def openai_provider() -> tuple[str, str, str] | None:
    """默认 OpenAI 通道（审核等通用），不回落到 DeepSeek。"""
    return openai_agent_provider('default')


def openai_agent_provider(agent: str) -> tuple[str, str, str] | None:
    """按智能体角色返回独立 OpenAI 密钥。

    环境变量约定（未配置时回退 OPENAI_API_KEY）：
    - profile_interpreter → OPENAI_PROFILE_INTERPRETER_API_KEY
    - knowledge_retriever → OPENAI_KNOWLEDGE_RETRIEVER_API_KEY
    - instructional_designer → OPENAI_INSTRUCTIONAL_DESIGNER_API_KEY
    - path_planner → OPENAI_PATH_PLANNER_API_KEY
    - quality_reviewer / default → OPENAI_API_KEY
    """
    if _blocked_in_tests():
        return None
    role = (agent or 'default').strip().lower()
    env_by_role = {
        'profile_interpreter': 'OPENAI_PROFILE_INTERPRETER_API_KEY',
        'knowledge_retriever': 'OPENAI_KNOWLEDGE_RETRIEVER_API_KEY',
        'instructional_designer': 'OPENAI_INSTRUCTIONAL_DESIGNER_API_KEY',
        'path_planner': 'OPENAI_PATH_PLANNER_API_KEY',
        'quality_reviewer': 'OPENAI_API_KEY',
        'default': 'OPENAI_API_KEY',
    }
    env_name = env_by_role.get(role, 'OPENAI_API_KEY')
    api_key = os.getenv(env_name, '').strip() or os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        return None
    base = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    model_env = {
        'profile_interpreter': 'OPENAI_PROFILE_INTERPRETER_MODEL',
        'knowledge_retriever': 'OPENAI_KNOWLEDGE_RETRIEVER_MODEL',
        'instructional_designer': 'OPENAI_INSTRUCTIONAL_DESIGNER_MODEL',
        'path_planner': 'OPENAI_PATH_PLANNER_MODEL',
    }.get(role)
    model = (
        (os.getenv(model_env, '').strip() if model_env else '')
        or os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip()
        or 'gpt-4o-mini'
    )
    return (
        api_key,
        f'{base}/chat/completions',
        model,
    )


def llm_provider() -> tuple[str, str, str] | None:
    """返回 (api_key, endpoint, model)，优先 DeepSeek，其次 OpenRouter。"""
    if _blocked_in_tests():
        return None
    deepseek = os.getenv('DEEPSEEK_API_KEY', '').strip()
    if deepseek:
        return _deepseek_tuple(deepseek)
    openrouter = os.getenv('OPENROUTER_API_KEY', '').strip()
    if openrouter:
        return (
            openrouter,
            'https://openrouter.ai/api/v1/chat/completions',
            os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
        )
    return openai_provider()


def messenger_provider() -> tuple[str, str, str] | None:
    """驿站助手 / 小E 对话专用 DeepSeek 密钥。"""
    if _blocked_in_tests():
        return None
    key = (
        os.getenv('DEEPSEEK_MESSENGER_API_KEY', '').strip()
        or os.getenv('DEEPSEEK_API_KEY', '').strip()
    )
    return _deepseek_tuple(key) if key else None


def emergency_provider() -> tuple[str, str, str] | None:
    """边界条件补给站 · 成长轨迹 AI 解析专用 DeepSeek 密钥。"""
    if _blocked_in_tests():
        return None
    key = (
        os.getenv('DEEPSEEK_EMERGENCY_API_KEY', '').strip()
        or os.getenv('DEEPSEEK_API_KEY', '').strip()
    )
    return _deepseek_tuple(key) if key else None


def learning_path_provider() -> tuple[str, str, str] | None:
    """小E 学习路径建议专用 DeepSeek 密钥。"""
    if _blocked_in_tests():
        return None
    key = (
        os.getenv('DEEPSEEK_LEARNING_PATH_API_KEY', '').strip()
        or os.getenv('DEEPSEEK_API_KEY', '').strip()
    )
    return _deepseek_tuple(key) if key else None


def api_key_configured() -> bool:
    return llm_provider() is not None


def strip_asterisks(text: str) -> str:
    """移除 Markdown 星号，避免学生端出现 ** 加粗。"""
    cleaned = (text or '').strip()
    previous = None
    while cleaned and previous != cleaned:
        previous = cleaned
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\*([^*\n]+)\*', r'\1', cleaned)
    return cleaned.strip()


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
    timeout: float = 12.0,
    max_tokens: int = 640,
    provider: tuple[str, str, str] | None = None,
    temperature: float = 0.4,
    force_json_object: bool = False,
) -> dict[str, Any] | None:
    """调用 LLM 并解析 JSON 对象响应。"""
    provider = provider or llm_provider()
    if not provider:
        return None
    api_key, endpoint, model = provider
    payload: dict[str, Any] = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'max_tokens': max_tokens,
        'temperature': temperature,
    }
    if force_json_object:
        payload['response_format'] = {'type': 'json_object'}
    try:
        resp = direct_post(
            endpoint,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
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
    timeout: float = 12.0,
    max_tokens: int = 900,
    provider: tuple[str, str, str] | None = None,
) -> str | None:
    """调用 LLM 并返回纯文本回复。"""
    provider = provider or llm_provider()
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
        resp = direct_post(
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
        return strip_asterisks(str(content or '')) or None
    except Exception:
        return None
