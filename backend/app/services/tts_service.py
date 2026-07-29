"""讯飞在线语音合成（TTS）服务。

将讲解文稿合成为 MP3 并落盘到 ``MEDIA_ROOT/audio``，返回可通过
``/api/v1/media/audio/<filename>`` 访问的相对 URL。未配置凭证或合成失败时
返回 ``None``，调用方保留 ``audio_fallback`` 文稿兜底。

凭证（三项均必填）：
- ``IFLYTEK_TTS_APP_ID``
- ``IFLYTEK_TTS_API_KEY``
- ``IFLYTEK_TTS_API_SECRET``
可选：``IFLYTEK_TTS_VOICE``（默认 xiaoyan）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import ssl
import uuid
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlencode

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT', str(BACKEND_ROOT / 'media')))

TTS_HOST = 'tts-api.xfyun.cn'
TTS_PATH = '/v2/tts'
TTS_URL = f'wss://{TTS_HOST}{TTS_PATH}'


class IflytekTtsService:
    MAX_TEXT_LENGTH = 2000

    @staticmethod
    def _credentials() -> tuple[str, str, str] | None:
        app_id = (os.getenv('IFLYTEK_TTS_APP_ID') or '').strip()
        api_key = (os.getenv('IFLYTEK_TTS_API_KEY') or '').strip()
        api_secret = (os.getenv('IFLYTEK_TTS_API_SECRET') or '').strip()
        if app_id and api_key and api_secret:
            return app_id, api_key, api_secret
        return None

    @classmethod
    def configured(cls) -> bool:
        return cls._credentials() is not None

    @staticmethod
    def _auth_url(api_key: str, api_secret: str) -> str:
        date = format_datetime(datetime.now(timezone.utc), usegmt=True)
        signature_origin = f'host: {TTS_HOST}\ndate: {date}\nGET {TTS_PATH} HTTP/1.1'
        signature = base64.b64encode(
            hmac.new(api_secret.encode(), signature_origin.encode(), hashlib.sha256).digest()
        ).decode()
        authorization_origin = (
            f'api_key="{api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode()).decode()
        return TTS_URL + '?' + urlencode({'authorization': authorization, 'date': date, 'host': TTS_HOST})

    @classmethod
    def synthesize(cls, text: str) -> bytes | None:
        """合成 MP3 字节流；未配置或失败返回 None。"""
        credentials = cls._credentials()
        if not credentials:
            return None
        text = (text or '').strip()[: cls.MAX_TEXT_LENGTH]
        if not text:
            return None
        app_id, api_key, api_secret = credentials
        try:
            import websocket  # websocket-client
        except ImportError:
            return None

        payload = {
            'common': {'app_id': app_id},
            'business': {
                'aue': 'lame',
                'sfl': 1,
                'auf': 'audio/L16;rate=16000',
                'vcn': os.getenv('IFLYTEK_TTS_VOICE', 'xiaoyan'),
                'speed': 50,
                'volume': 60,
                'pitch': 50,
                'tte': 'utf8',
            },
            'data': {
                'status': 2,
                'text': base64.b64encode(text.encode('utf-8')).decode(),
            },
        }
        chunks: list[bytes] = []
        try:
            ws = websocket.create_connection(
                cls._auth_url(api_key, api_secret),
                timeout=30,
                sslopt={'cert_reqs': ssl.CERT_NONE},
            )
            try:
                ws.send(json.dumps(payload))
                while True:
                    message = json.loads(ws.recv())
                    if message.get('code') != 0:
                        return None
                    data = message.get('data') or {}
                    audio = data.get('audio')
                    if audio:
                        chunks.append(base64.b64decode(audio))
                    if data.get('status') == 2:
                        break
            finally:
                ws.close()
        except Exception:
            return None
        return b''.join(chunks) or None


class EdgeTtsService:
    """微软 Edge 免费 TTS 兜底：无需密钥，演示与无讯飞凭证时使用。"""

    VOICE = os.getenv('EDGE_TTS_VOICE', 'zh-CN-XiaoxiaoNeural')

    @classmethod
    def configured(cls) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def synthesize(cls, text: str) -> bytes | None:
        text = (text or '').strip()[:2000]
        if not text or not cls.configured():
            return None
        try:
            import asyncio
            import edge_tts

            async def _run() -> bytes:
                communicate = edge_tts.Communicate(text, cls.VOICE)
                chunks: list[bytes] = []
                async for chunk in communicate.stream():
                    if chunk.get('type') == 'audio':
                        chunks.append(chunk['data'])
                return b''.join(chunks)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        return pool.submit(asyncio.run, _run()).result(timeout=60)
                return loop.run_until_complete(_run())
            except RuntimeError:
                return asyncio.run(_run())
        except Exception:
            return None


class LocalTtsService:
    """Windows SAPI / pyttsx3 离线兜底，外网不可用时仍可演示语音讲解。"""

    @classmethod
    def configured(cls) -> bool:
        try:
            import pyttsx3  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def synthesize(cls, text: str) -> tuple[bytes, str] | None:
        text = (text or '').strip()[:800]
        if not text or not cls.configured():
            return None
        try:
            import tempfile
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                path = tmp.name
            try:
                engine.save_to_file(text, path)
                engine.runAndWait()
                data = Path(path).read_bytes()
            finally:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
            return (data, 'wav') if data else None
        except Exception:
            return None


class TtsService:
    """统一 TTS 入口：讯飞 → Edge → 本地 SAPI。"""

    @classmethod
    def configured(cls) -> bool:
        return (
            IflytekTtsService.configured()
            or EdgeTtsService.configured()
            or LocalTtsService.configured()
        )

    @classmethod
    def synthesize_to_media(cls, text: str, prefix: str = 'lesson') -> str | None:
        audio = IflytekTtsService.synthesize(text)
        backend = 'iflytek'
        ext = 'mp3'
        if not audio:
            audio = EdgeTtsService.synthesize(text)
            backend = 'edge'
        if not audio:
            local = LocalTtsService.synthesize(text)
            if local:
                audio, ext = local
                backend = 'local'
        if not audio:
            return None
        audio_dir = MEDIA_ROOT / 'audio'
        audio_dir.mkdir(parents=True, exist_ok=True)
        filename = f'{prefix}-{backend}-{uuid.uuid4().hex[:12]}.{ext}'
        (audio_dir / filename).write_bytes(audio)
        return f'/api/v1/media/audio/{filename}'


@classmethod  # type: ignore[misc]
def _legacy_synthesize_to_media(cls, text: str, prefix: str = 'lesson') -> str | None:
    return TtsService.synthesize_to_media(text, prefix)


IflytekTtsService.synthesize_to_media = _legacy_synthesize_to_media  # type: ignore[method-assign]
