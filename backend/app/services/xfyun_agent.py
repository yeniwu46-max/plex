"""iFlytek Xingchen Agent API adapter for Messenger replies."""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import requests
from agents.http_client import direct_post
from flask import current_app, has_app_context

logger = logging.getLogger(__name__)


class XfyunAgentServiceError(RuntimeError):
    def __init__(self, code: str, message: str, *, recoverable: bool = True):
        super().__init__(message)
        self.code = code
        self.recoverable = recoverable


class XfyunAgentService:
    DEFAULT_URL = 'https://xingchen-api.xf-yun.com/workflow/v1/chat/completions'
    DEFAULT_BOT_ID = '5709919'
    DEFAULT_USER_INPUT_KEY = 'AGENT_USER_INPUT'
    _last_result: dict[str, Any] = {
        'status': 'unavailable',
        'flow_id': None,
        'latency_ms': None,
        'error_code': 'not_checked',
    }

    @staticmethod
    def configured() -> bool:
        if has_app_context() and current_app.config.get('TESTING') and not current_app.config.get('XFYUN_AGENT_ALLOW_IN_TESTS'):
            return False
        return bool(
            os.getenv('XFYUN_AGENT_FLOW_ID', '').strip()
            and os.getenv('XFYUN_AGENT_API_KEY', '').strip()
            and os.getenv('XFYUN_AGENT_API_SECRET', '').strip()
        )

    @classmethod
    def status(cls) -> dict[str, Any]:
        return {
            'configured': cls.configured(),
            'backend': 'xfyun_agent' if cls.configured() else 'unavailable',
            'bot_id': os.getenv('XFYUN_AGENT_BOT_ID', cls.DEFAULT_BOT_ID).strip() or cls.DEFAULT_BOT_ID,
            **cls._last_result,
        }

    @classmethod
    def _record(cls, **values):
        cls._last_result = {**cls._last_result, **values}

    @staticmethod
    def _extract_text(payload: Any) -> str:
        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, list):
            for item in payload:
                text = XfyunAgentService._extract_text(item)
                if text:
                    return text
            return ''
        if not isinstance(payload, dict):
            return ''

        choices = payload.get('choices')
        if isinstance(choices, list) and choices:
            for key in ('message', 'delta'):
                text = XfyunAgentService._extract_text(choices[0].get(key))
                if text:
                    return text

        for key in ('content', 'answer', 'text', 'output', 'result'):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for key in ('data', 'message', 'response'):
            text = XfyunAgentService._extract_text(payload.get(key))
            if text:
                return text
        return ''

    @staticmethod
    def _error_code(payload: Any) -> int | None:
        if not isinstance(payload, dict):
            return None
        code = payload.get('code')
        return code if isinstance(code, int) else None

    @classmethod
    def chat_text(cls, *, user_id: int, message: str, context: str = '', timeout: int = 90) -> str:
        flow_id = os.getenv('XFYUN_AGENT_FLOW_ID', '').strip()
        api_key = os.getenv('XFYUN_AGENT_API_KEY', '').strip()
        api_secret = os.getenv('XFYUN_AGENT_API_SECRET', '').strip()
        if not flow_id or not api_key or not api_secret:
            cls._record(status='unavailable', flow_id=None, latency_ms=None, error_code='not_configured')
            raise XfyunAgentServiceError('not_configured', 'xfyun_agent_not_configured')

        user_input_key = os.getenv('XFYUN_AGENT_USER_INPUT_KEY', cls.DEFAULT_USER_INPUT_KEY).strip() or cls.DEFAULT_USER_INPUT_KEY
        user_input = f'{context}\n\nStudent question: {message}'.strip()
        started = time.monotonic()
        try:
            response = direct_post(
                os.getenv('XFYUN_AGENT_URL', cls.DEFAULT_URL).strip() or cls.DEFAULT_URL,
                headers={
                    'Authorization': f'Bearer {api_key}:{api_secret}',
                    'Content-Type': 'application/json',
                },
                json={
                    'flow_id': flow_id,
                    'uid': f'a3-student-{user_id}',
                    'parameters': {user_input_key: user_input},
                    'stream': False,
                    'ext': {
                        'bot_id': os.getenv('XFYUN_AGENT_BOT_ID', cls.DEFAULT_BOT_ID).strip() or cls.DEFAULT_BOT_ID,
                        'caller': 'a3-messenger',
                    },
                },
                proxies={'http': '', 'https': ''},
                timeout=(3, timeout),
            )
            latency_ms = round((time.monotonic() - started) * 1000)
            if response.status_code in (401, 403):
                raise XfyunAgentServiceError('authentication_failed', 'xfyun_agent_authentication_failed', recoverable=False)
            if response.status_code == 429:
                raise XfyunAgentServiceError('rate_limited', 'xfyun_agent_rate_limited')
            if response.status_code >= 500:
                raise XfyunAgentServiceError('upstream_error', f'xfyun_agent_upstream_{response.status_code}')
            if response.status_code >= 400:
                raise XfyunAgentServiceError('request_rejected', f'xfyun_agent_http_{response.status_code}', recoverable=False)

            payload = response.json()
            code = cls._error_code(payload)
            if code not in (None, 0):
                message = payload.get('message') if isinstance(payload, dict) else ''
                raise XfyunAgentServiceError('workflow_error', str(message or f'xfyun_agent_code_{code}'))

            text = cls._extract_text(payload)
            if not text:
                raise XfyunAgentServiceError('empty_response', 'xfyun_agent_content_empty')
            if re.fullmatch(r'\{\{[^{}]+\}\}\s*', text):
                raise XfyunAgentServiceError('placeholder_response', 'xfyun_agent_placeholder_response')
            cls._record(status='available', flow_id=flow_id, latency_ms=latency_ms, error_code=None)
            logger.info('Xfyun Agent request succeeded flow_id=%s latency_ms=%s', flow_id, latency_ms)
            return text
        except requests.Timeout as exc:
            cls._record(status='unavailable', flow_id=flow_id, error_code='timeout')
            raise XfyunAgentServiceError('timeout', 'xfyun_agent_timeout') from exc
        except requests.RequestException as exc:
            cls._record(status='unavailable', flow_id=flow_id, error_code='network_error')
            raise XfyunAgentServiceError('network_error', 'xfyun_agent_network_error') from exc
        except (ValueError, TypeError) as exc:
            cls._record(status='unavailable', flow_id=flow_id, error_code='invalid_response')
            raise XfyunAgentServiceError('invalid_response', 'xfyun_agent_response_invalid') from exc
        except XfyunAgentServiceError as exc:
            cls._record(
                status='unavailable',
                flow_id=flow_id,
                latency_ms=round((time.monotonic() - started) * 1000),
                error_code=exc.code,
            )
            raise
