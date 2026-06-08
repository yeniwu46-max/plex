"""Hardened Spark Lite HTTP adapter with privacy-safe diagnostics."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class SparkServiceError(RuntimeError):
    def __init__(self, code: str, message: str, *, recoverable: bool = True):
        super().__init__(message)
        self.code = code
        self.recoverable = recoverable


class IflytekSparkService:
    DEFAULT_URL = 'https://spark-api-open.xf-yun.com/v1/chat/completions'
    _last_result: dict[str, Any] = {
        'status': 'unavailable',
        'request_id': None,
        'latency_ms': None,
        'model': None,
        'error_code': 'not_checked',
    }

    @staticmethod
    def configured() -> bool:
        return bool(os.getenv('IFLYTEK_SPARK_API_PASSWORD'))

    @classmethod
    def status(cls) -> dict[str, Any]:
        return {
            'configured': cls.configured(),
            'backend': 'iflytek_spark' if cls.configured() else 'unavailable',
            **cls._last_result,
        }

    @classmethod
    def _record(cls, **values):
        cls._last_result = {**cls._last_result, **values}

    @classmethod
    def chat_json(cls, system_prompt: str, user_prompt: str, timeout: int = 30) -> dict[str, Any]:
        password = os.getenv('IFLYTEK_SPARK_API_PASSWORD')
        if not password:
            cls._record(status='unavailable', error_code='not_configured')
            raise SparkServiceError('not_configured', 'iflytek_not_configured')

        url = os.getenv('IFLYTEK_SPARK_URL', cls.DEFAULT_URL)
        model = os.getenv('IFLYTEK_SPARK_MODEL', 'lite')
        started = time.monotonic()
        request_id = None
        try:
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
                timeout=(5, timeout),
            )
            request_id = (
                response.headers.get('x-request-id')
                or response.headers.get('request-id')
                or response.headers.get('sid')
            )
            latency_ms = round((time.monotonic() - started) * 1000)
            if response.status_code in (401, 403):
                raise SparkServiceError('authentication_failed', 'spark_authentication_failed', recoverable=False)
            if response.status_code == 429:
                raise SparkServiceError('rate_limited', 'spark_rate_limited')
            if response.status_code >= 500:
                raise SparkServiceError('upstream_error', f'spark_upstream_{response.status_code}')
            if response.status_code >= 400:
                raise SparkServiceError('request_rejected', f'spark_http_{response.status_code}', recoverable=False)

            try:
                payload = response.json()
                choices = payload.get('choices')
                if not isinstance(choices, list) or not choices:
                    raise SparkServiceError('invalid_response', 'spark_choices_missing')
                message = choices[0].get('message')
                text = message.get('content') if isinstance(message, dict) else None
                if not isinstance(text, str) or not text.strip():
                    raise SparkServiceError('empty_response', 'spark_content_empty')
                text = text.strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
                result = json.loads(text)
            except SparkServiceError:
                raise
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise SparkServiceError('invalid_json', 'spark_response_invalid_json') from exc

            if not isinstance(result, dict):
                raise SparkServiceError('invalid_response', 'spark_response_not_object')
            cls._record(
                status='available',
                request_id=request_id,
                latency_ms=latency_ms,
                model=model,
                error_code=None,
            )
            logger.info(
                'Spark request succeeded request_id=%s model=%s latency_ms=%s',
                request_id or 'unknown',
                model,
                latency_ms,
            )
            return result
        except requests.Timeout as exc:
            error = SparkServiceError('timeout', 'spark_timeout')
            cls._record(status='unavailable', request_id=request_id, model=model, error_code=error.code)
            raise error from exc
        except requests.RequestException as exc:
            error = SparkServiceError('network_error', 'spark_network_error')
            cls._record(status='unavailable', request_id=request_id, model=model, error_code=error.code)
            raise error from exc
        except SparkServiceError as exc:
            cls._record(
                status='unavailable',
                request_id=request_id,
                latency_ms=round((time.monotonic() - started) * 1000),
                model=model,
                error_code=exc.code,
            )
            logger.warning(
                'Spark request failed request_id=%s model=%s error_code=%s',
                request_id or 'unknown',
                model,
                exc.code,
            )
            raise
