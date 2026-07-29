"""Hardened Spark Lite HTTP adapter with privacy-safe diagnostics."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import requests
from agents.http_client import direct_post
from flask import current_app, has_app_context

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
        # Unit/integration tests must not depend on a developer's local Spark
        # credential or the provider's availability.  Explicit tests of this
        # adapter call ``chat_json`` with a mocked transport directly.
        if has_app_context() and current_app.config.get('TESTING') and not current_app.config.get('SPARK_ALLOW_IN_TESTS'):
            return False
        return bool(IflytekSparkService._resolve_api_password())

    @staticmethod
    def _resolve_api_password(purpose: str | None = None) -> str:
        """Resolve Bearer token from env (supports appId:apiKey combined credentials).

        purpose='trial_analysis' 时优先使用试炼分析专用密钥，避免覆盖驿站小E凭证。
        purpose='supply_station' 时优先使用补给站专用密钥，与小E/试炼凭证隔离。
        """
        if purpose == 'trial_analysis':
            trial_cred = (
                os.getenv('IFLYTEK_SPARK_TRIAL_CREDENTIALS', '').strip()
                or os.getenv('IFLYTEK_SPARK_TRIAL_API_PASSWORD', '').strip()
            )
            if trial_cred:
                return trial_cred
        if purpose == 'supply_station':
            supply_cred = (
                os.getenv('IFLYTEK_SPARK_SUPPLY_CREDENTIALS', '').strip()
                or os.getenv('IFLYTEK_SPARK_SUPPLY_API_PASSWORD', '').strip()
            )
            if supply_cred:
                return supply_cred
        direct = os.getenv('IFLYTEK_SPARK_API_PASSWORD', '').strip()
        if direct:
            return direct
        combined = os.getenv('IFLYTEK_SPARK_CREDENTIALS', '').strip()
        if combined:
            return combined
        app_id = os.getenv('IFLYTEK_SPARK_APP_ID', '').strip()
        api_key = os.getenv('IFLYTEK_SPARK_API_KEY', '').strip()
        if app_id and api_key:
            return f'{app_id}:{api_key}'
        return ''

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

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        """Accept JSON wrapped in a markdown fence or a short model preface."""
        cleaned = text.strip()
        fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, flags=re.IGNORECASE | re.DOTALL)
        if fenced:
            cleaned = fenced.group(1)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start, end = cleaned.find('{'), cleaned.rfind('}')
            if start < 0 or end <= start:
                raise
            parsed = json.loads(cleaned[start:end + 1])
        if not isinstance(parsed, dict):
            raise ValueError('spark_response_not_object')
        return parsed

    @classmethod
    def chat_json(
        cls,
        system_prompt: str,
        user_prompt: str,
        timeout: int = 30,
        *,
        purpose: str | None = None,
    ) -> dict[str, Any]:
        password = cls._resolve_api_password(purpose)
        if not password:
            cls._record(status='unavailable', error_code='not_configured')
            raise SparkServiceError('not_configured', 'iflytek_not_configured')

        url = os.getenv('IFLYTEK_SPARK_URL', cls.DEFAULT_URL)
        model = os.getenv('IFLYTEK_SPARK_MODEL', 'lite')
        started = time.monotonic()
        request_id = None
        try:
            response = direct_post(
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
                timeout=(3, timeout),
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
                result = cls._parse_json_object(text)
            except SparkServiceError:
                raise
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise SparkServiceError('invalid_json', 'spark_response_invalid_json') from exc

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

    @classmethod
    def chat_text(cls, system_prompt: str, user_prompt: str, timeout: int = 30) -> str:
        """Return the provider's natural-language response without a JSON contract."""
        password = cls._resolve_api_password()
        if not password:
            cls._record(status='unavailable', error_code='not_configured')
            raise SparkServiceError('not_configured', 'iflytek_not_configured')

        url = os.getenv('IFLYTEK_SPARK_URL', cls.DEFAULT_URL)
        model = os.getenv('IFLYTEK_SPARK_MODEL', 'lite')
        started = time.monotonic()
        request_id = None
        try:
            response = direct_post(
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
                timeout=(3, timeout),
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

            payload = response.json()
            choices = payload.get('choices') if isinstance(payload, dict) else None
            message = choices[0].get('message') if isinstance(choices, list) and choices else None
            text = message.get('content') if isinstance(message, dict) else None
            if not isinstance(text, str) or not text.strip():
                raise SparkServiceError('empty_response', 'spark_content_empty')

            cls._record(status='available', request_id=request_id, latency_ms=latency_ms, model=model, error_code=None)
            logger.info('Spark text request succeeded request_id=%s model=%s latency_ms=%s', request_id or 'unknown', model, latency_ms)
            return text.strip()
        except requests.Timeout as exc:
            error = SparkServiceError('timeout', 'spark_timeout')
            cls._record(status='unavailable', request_id=request_id, model=model, error_code=error.code)
            raise error from exc
        except requests.RequestException as exc:
            error = SparkServiceError('network_error', 'spark_network_error')
            cls._record(status='unavailable', request_id=request_id, model=model, error_code=error.code)
            raise error from exc
        except (ValueError, KeyError, TypeError) as exc:
            error = SparkServiceError('invalid_response', 'spark_response_invalid')
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
            logger.warning('Spark text request failed request_id=%s model=%s error_code=%s', request_id or 'unknown', model, exc.code)
            raise
