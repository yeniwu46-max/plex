"""OpenAI 兼容流式（SSE）LLM 客户端与 Flask SSE 工具。

驿站答疑 / 画像对话的流式端点共用本模块：
- ``iter_openai_stream``：对任意 OpenAI 兼容端点发起 ``stream=True`` 请求并逐段产出增量文本；
- ``stream_provider_chain``：按 DeepSeek → 讯飞星火（OpenAI 兼容）顺序返回可用的流式供应商；
- ``sse_event`` / ``sse_headers``：SSE 帧编码与响应头。
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterator

from agents.http_client import direct_post
from agents.llm_client import llm_provider, messenger_provider


def sse_event(data: dict) -> str:
    """Encode one Server-Sent Events frame."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_headers() -> dict:
    return {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }


def chunk_text(text: str, size: int = 18) -> Iterator[str]:
    """将整段文本切成小块，用于非流式来源的伪流式呈现。"""
    text = text or ''
    for start in range(0, len(text), size):
        yield text[start:start + size]


def _spark_stream_provider() -> tuple[str, str, str] | None:
    from app.services.iflytek_spark import IflytekSparkService

    password = IflytekSparkService._resolve_api_password()
    if not password:
        return None
    return (
        password,
        os.getenv('IFLYTEK_SPARK_URL', IflytekSparkService.DEFAULT_URL),
        os.getenv('IFLYTEK_SPARK_MODEL', 'lite'),
    )


def stream_provider_chain(purpose: str = 'messenger') -> list[tuple[str, str, str]]:
    """按优先级返回 (api_key, endpoint, model) 流式供应商列表。

    驿站小E：优先讯飞星火（通常更稳更快），再回落 DeepSeek。
    其他用途：保持 DeepSeek / 通用 LLM 优先。
    """
    providers: list[tuple[str, str, str]] = []
    spark = _spark_stream_provider()
    primary = messenger_provider() if purpose == 'messenger' else llm_provider()
    if purpose == 'messenger':
        if spark:
            providers.append(spark)
        if primary:
            providers.append(primary)
    else:
        if primary:
            providers.append(primary)
        if spark:
            providers.append(spark)
    return providers


def iter_openai_stream(
    provider: tuple[str, str, str],
    messages: list[dict],
    *,
    temperature: float = 0.55,
    max_tokens: int = 900,
    timeout: tuple[float, float] = (3, 5),
) -> Iterator[str]:
    """对 OpenAI 兼容端点发起流式请求，逐段产出增量文本。

    连接失败、HTTP 错误会在产出首个增量之前抛出异常，调用方可以借此
    安全地切换到下一个供应商或非流式兜底。
    """
    api_key, endpoint, model = provider
    response = direct_post(
        endpoint,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        json={
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': True,
        },
        stream=True,
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        for raw in response.iter_lines():
            if not raw:
                continue
            line = raw.decode('utf-8', errors='ignore').strip()
            if not line.startswith('data:'):
                continue
            data = line[5:].strip()
            if data == '[DONE]':
                break
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = payload.get('choices')
            if not isinstance(choices, list) or not choices:
                continue
            delta = choices[0].get('delta') or {}
            text = delta.get('content')
            if isinstance(text, str) and text:
                yield text
    finally:
        response.close()
