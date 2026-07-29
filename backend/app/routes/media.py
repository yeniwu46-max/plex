"""生成媒体文件（TTS 音频 / 教学视频等）静态服务。"""
import re

from flask import Blueprint, abort, send_from_directory

from app.services.tts_service import MEDIA_ROOT

media_bp = Blueprint('media', __name__, url_prefix='/api/v1/media')

_SAFE_NAME = re.compile(r'^[A-Za-z0-9._-]+$')


@media_bp.route('/<category>/<filename>', methods=['GET'])
def get_media(category: str, filename: str):
    if not _SAFE_NAME.match(category) or not _SAFE_NAME.match(filename):
        abort(404)
    directory = MEDIA_ROOT / category
    if not directory.is_dir():
        abort(404)
    return send_from_directory(directory, filename, conditional=True)
