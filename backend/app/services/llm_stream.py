"""OpenAI 兼容流式（SSE）LLM 客户端与 Flask SSE 工具。

驿站答疑 / 画像对话的流式端点共用本模块：
- ``iter_openai_stream``：对任意 OpenAI 兼容端点发起 ``stream=True`` 请求并逐段产出增量文本；
- ``stream_provider_chain``：按用途返回可用的流式供应商；
- ``sse_event`` / ``sse_headers``：SSE 帧编码与响应头。
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterator

from agents.http_client import direct_post
from agents.llm_client import llm_provider, messenger_provider


def sse_event(data: dict) -> str:
    """Encode one Server-Sent Events frame.

    Append a padding comment so proxies / WSGI buffers are more likely to flush
    small early frames (first stage / first token) without waiting for a full buffer.
    """
    payload = json.dumps(data, ensure_ascii=False)
    # 注释填充帮助冲刷中间件缓冲，又不影响 EventSource / fetch SSE 解析
    return f"data: {payload}\n\n: {' ' * 256}\n\n"


def sse_headers() -> dict:
    return {
        'Cache-Control': 'no-cache, no-transform',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
        'Content-Type': 'text/event-stream; charset=utf-8',
    }


def chunk_text(text: str, size: int = 12) -> Iterator[str]:
    """将整段文本切成小块，用于非流式来源的伪流式呈现。"""
    text = text or ''
    for start in range(0, len(text), size):
        yield text[start:start + size]


def _spark_stream_provider(purpose: str | None = None) -> tuple[str, str, str] | None:
    from app.services.iflytek_spark import IflytekSparkService

    # messenger / 默认 → 驿站流式凭证；trial_* → 试炼/辅导凭证
    spark_purpose = purpose
    if purpose in {'profile'}:
        spark_purpose = 'messenger'
    password = IflytekSparkService._resolve_api_password(spark_purpose)
    if not password:
        return None
    return (
        password,
        os.getenv('IFLYTEK_SPARK_URL', IflytekSparkService.DEFAULT_URL),
        os.getenv('IFLYTEK_SPARK_MODEL', 'lite'),
    )


def stream_provider_chain(purpose: str = 'messenger') -> list[tuple[str, str, str]]:
    """按优先级返回 (api_key, endpoint, model) 流式供应商列表。

    全用途统一：DeepSeek 优先；仅在已配置且可用时把讯飞星火放在兜底。
    （星辰 Agent 无 OpenAI 兼容流式，不进入本链，避免假配置拖死首 token。）
    """
    providers: list[tuple[str, str, str]] = []
    spark = _spark_stream_provider(purpose)
    primary = messenger_provider() if purpose == 'messenger' else llm_provider()
    if primary:
        providers.append(primary)
    if spark:
        providers.append(spark)
    # 去重（同一 endpoint+model+key 不重复尝试）
    deduped: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in providers:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def iter_openai_stream(
    provider: tuple[str, str, str],
    messages: list[dict],
    *,
    temperature: float = 0.55,
    max_tokens: int = 900,
    timeout: tuple[float, float] = (3, 45),
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
            'Accept': 'text/event-stream',
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
        # decode_unicode + chunk_size 有助于尽快吐出首包，减轻卡顿感
        for raw in response.iter_lines(decode_unicode=True, chunk_size=64):
            if not raw:
                continue
            line = raw.strip() if isinstance(raw, str) else raw.decode('utf-8', errors='ignore').strip()
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
