"""Minimal Spark Lite HTTP adapter with strict JSON extraction."""
from __future__ import annotations

import json
import os
from typing import Any

import requests


class IflytekSparkService:
    DEFAULT_URL = 'https://spark-api-open.xf-yun.com/v1/chat/completions'

    @staticmethod
    def configured() -> bool:
        return bool(os.getenv('IFLYTEK_SPARK_API_PASSWORD'))

    @staticmethod
    def chat_json(system_prompt: str, user_prompt: str, timeout: int = 30) -> dict[str, Any]:
        password = os.getenv('IFLYTEK_SPARK_API_PASSWORD')
        if not password:
            raise RuntimeError('iflytek_not_configured')
        url = os.getenv('IFLYTEK_SPARK_URL', IflytekSparkService.DEFAULT_URL)
        model = os.getenv('IFLYTEK_SPARK_MODEL', 'lite')
        response = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {password}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'temperature': 0.3,
                'stream': False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload['choices'][0]['message']['content'].strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError('spark_response_not_object')
        return result
