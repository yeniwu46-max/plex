"""火山方舟（Ark）多模态生成服务：教学短视频与答疑图解。

- 图像：``/images/generations`` 同步返回 URL，下载到 ``MEDIA_ROOT/image``；
  默认模型 Seedream 5.0 Pro（``doubao-seedream-5-0-pro-260628``），
  ``size`` 支持 ``2K`` / ``1K`` / ``1024x1024`` 等；
- 视频：``/contents/generations/tasks`` 创建任务后轮询，成功后下载到
  ``MEDIA_ROOT/video``。

凭证：``ARK_API_KEY``；模型：``ARK_VIDEO_MODEL`` / ``ARK_IMAGE_MODEL``。
未配置或失败时所有方法返回 ``None``，调用方自行降级。
"""
from __future__ import annotations

import os
import time
import uuid

from agents.http_client import direct_get, direct_post
from app.services.tts_service import MEDIA_ROOT

DEFAULT_BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
DEFAULT_IMAGE_MODEL = 'doubao-seedream-5-0-pro-260628'
DEFAULT_IMAGE_SIZE = '2K'


class ArkMediaService:
    @staticmethod
    def _api_key() -> str:
        return (os.getenv('ARK_API_KEY') or '').strip()

    @staticmethod
    def _base_url() -> str:
        return (os.getenv('ARK_BASE_URL') or DEFAULT_BASE_URL).rstrip('/')

    @classmethod
    def _headers(cls) -> dict:
        return {
            'Authorization': f'Bearer {cls._api_key()}',
            'Content-Type': 'application/json',
        }

    @classmethod
    def _image_model(cls) -> str:
        return (os.getenv('ARK_IMAGE_MODEL') or DEFAULT_IMAGE_MODEL).strip()

    @classmethod
    def _image_size(cls, size: str | None = None) -> str:
        if size and str(size).strip():
            return str(size).strip()
        return (os.getenv('ARK_IMAGE_SIZE') or DEFAULT_IMAGE_SIZE).strip() or DEFAULT_IMAGE_SIZE

    @classmethod
    def _image_watermark(cls) -> bool:
        raw = (os.getenv('ARK_IMAGE_WATERMARK') or 'true').strip().lower()
        return raw in ('1', 'true', 'yes', 'on')

    @classmethod
    def image_configured(cls) -> bool:
        return bool(cls._api_key() and cls._image_model())

    @classmethod
    def video_configured(cls) -> bool:
        return bool(cls._api_key() and (os.getenv('ARK_VIDEO_MODEL') or '').strip())

    @staticmethod
    def _download_to_media(url: str, category: str, suffix: str) -> str | None:
        try:
            response = direct_get(url, timeout=(10, 120), stream=True)
            response.raise_for_status()
            directory = MEDIA_ROOT / category
            directory.mkdir(parents=True, exist_ok=True)
            filename = f'{category}-{uuid.uuid4().hex[:12]}{suffix}'
            path = directory / filename
            with open(path, 'wb') as handle:
                for chunk in response.iter_content(chunk_size=1 << 16):
                    handle.write(chunk)
            return f'/api/v1/media/{category}/{filename}'
        except Exception:
            return None

    # ---------- 图像生成（答疑图解） ----------

    @classmethod
    def generate_image(cls, prompt: str, *, size: str | None = None) -> str | None:
        """文生图并落盘，返回本地媒体 URL；失败返回 None。

        对齐方舟 OpenAI 兼容接口::

            client.images.generate(
                model="doubao-seedream-5-0-pro-260628",
                prompt=...,
                size="2K",
                response_format="url",
                extra_body={"watermark": True},
            )
        """
        if not cls.image_configured():
            return None
        text = (prompt or '').strip()[:2000]
        if not text:
            return None
        try:
            response = direct_post(
                f'{cls._base_url()}/images/generations',
                headers=cls._headers(),
                json={
                    'model': cls._image_model(),
                    'prompt': text,
                    'size': cls._image_size(size),
                    'response_format': 'url',
                    'watermark': cls._image_watermark(),
                },
                # 答疑图解：短超时，避免阻塞对话收尾
                timeout=(3, 8),
            )
            response.raise_for_status()
            data = response.json().get('data') or []
            remote_url = data[0].get('url') if data else None
            if not remote_url:
                return None
            return cls._download_to_media(remote_url, 'image', '.png')
        except Exception:
            return None

    # ---------- 视频生成（教学短视频） ----------

    @classmethod
    def create_video_task(cls, prompt: str) -> str | None:
        if not cls.video_configured():
            return None
        try:
            response = direct_post(
                f'{cls._base_url()}/contents/generations/tasks',
                headers=cls._headers(),
                json={
                    'model': os.getenv('ARK_VIDEO_MODEL', '').strip(),
                    'content': [{'type': 'text', 'text': prompt[:800]}],
                },
                timeout=(10, 30),
            )
            response.raise_for_status()
            return response.json().get('id') or None
        except Exception:
            return None

    @classmethod
    def poll_video_task(cls, task_id: str) -> tuple[str, str | None]:
        """返回 (status, video_url)；status ∈ queued/running/succeeded/failed。"""
        try:
            response = direct_get(
                f'{cls._base_url()}/contents/generations/tasks/{task_id}',
                headers=cls._headers(),
                timeout=(10, 30),
            )
            response.raise_for_status()
            payload = response.json()
            status = payload.get('status') or 'running'
            video_url = None
            content = payload.get('content') or {}
            if isinstance(content, dict):
                video_url = content.get('video_url')
            return status, video_url
        except Exception:
            return 'failed', None

    @classmethod
    def generate_video(cls, prompt: str, *, max_wait_seconds: int = 240) -> str | None:
        """阻塞式生成视频并落盘，返回本地媒体 URL；超时或失败返回 None。"""
        task_id = cls.create_video_task(prompt)
        if not task_id:
            return None
        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            status, remote_url = cls.poll_video_task(task_id)
            if status == 'succeeded' and remote_url:
                return cls._download_to_media(remote_url, 'video', '.mp4')
            if status in ('failed', 'cancelled'):
                return None
            time.sleep(5)
        return None
