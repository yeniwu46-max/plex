# -*- coding: utf-8 -*-
"""知识点重排流水线共用的 DeepSeek 调用封装。

复用仓库既有的 provider 约定（`DEEPSEEK_TRIAL_GEN_API_KEY` → `DEEPSEEK_API_KEY`，
base/model 取 `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL`），与
app/services/ai_question_generator.py 用的是同一套凭证，不另起配置。

所有调用都要求模型输出纯 JSON；解析失败时返回 None 由调用方决定降级策略，
绝不把解析不出来的内容当成有效结果写库。
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

_JSON_BLOCK_RE = re.compile(r'```(?:json)?\s*(.*?)```', re.S)


class AiUnavailable(RuntimeError):
    """没有配置可用的 API key。"""


def _config() -> tuple[str, str, str]:
    key = (os.getenv('DEEPSEEK_TRIAL_GEN_API_KEY') or os.getenv('DEEPSEEK_API_KEY') or '').strip()
    if not key:
        raise AiUnavailable('未配置 DEEPSEEK_TRIAL_GEN_API_KEY / DEEPSEEK_API_KEY')
    base = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1').rstrip('/')
    model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    return key, base, model


def chat(system: str, user: str, *, max_tokens: int = 2048, temperature: float = 0.2,
         retries: int = 3, timeout: int = 90) -> str | None:
    """调用 DeepSeek，返回文本内容；全部重试失败返回 None。"""
    key, base, model = _config()
    payload = json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': temperature,
        'max_tokens': max_tokens,
    }).encode('utf-8')

    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(
            f'{base}/chat/completions',
            data=payload,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
            return data['choices'][0]['message']['content']
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    print(f'    [AI] 调用失败（已重试 {retries} 次）: {type(last_error).__name__}: {last_error}')
    return None


def chat_json(system: str, user: str, **kwargs):
    """要求模型返回 JSON，解析成功才返回对象，否则 None。"""
    text = chat(system, user, **kwargs)
    if not text:
        return None
    candidate = text.strip()
    block = _JSON_BLOCK_RE.search(candidate)
    if block:
        candidate = block.group(1).strip()
    else:
        # 容忍模型在 JSON 前后附带说明文字：截取第一个 { 或 [ 到最后一个 } 或 ]
        start = min((p for p in (candidate.find('{'), candidate.find('[')) if p != -1), default=-1)
        end = max(candidate.rfind('}'), candidate.rfind(']'))
        if start != -1 and end > start:
            candidate = candidate[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        print(f'    [AI] JSON 解析失败: {exc}; 原始片段: {candidate[:160]}')
        return None


def is_available() -> bool:
    try:
        _config()
        return True
    except AiUnavailable:
        return False
