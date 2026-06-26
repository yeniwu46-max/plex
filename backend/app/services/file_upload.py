# -*- coding: utf-8 -*-
"""文件上传校验与存储服务。"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

# ─── 全局禁止类型 ────────────────────────────────────────────
BLOCKED_EXTENSIONS = {'.exe', '.bat', '.cmd', '.sh', '.ps1', '.msi', '.dll', '.scr'}

# ─── 场景 → 允许角色 ─────────────────────────────────────────
SCENE_ROLE_MATRIX: dict[str, list[str]] = {
    'code-file':              ['student'],
    'learning-report':        ['student'],
    'screenshot':             ['student'],
    'course-material':        ['teacher', 'admin'],
    'question-bank':          ['teacher', 'admin'],
    'assignment-attachment':  ['teacher', 'admin'],
    'knowledge-doc':          ['admin'],
    'system-config':          ['admin'],
    'graph-data':             ['admin'],
}

# ─── 场景 → 允许扩展名 & 大小上限 ─────────────────────────────
SCENE_RESTRICTIONS: dict[str, dict] = {
    'code-file':             {'exts': {'.py', '.txt'},                               'max_bytes': 2  * 1024 * 1024},
    'learning-report':       {'exts': {'.pdf', '.doc', '.docx', '.md'},                      'max_bytes': 10 * 1024 * 1024},
    'screenshot':            {'exts': {'.png', '.jpg', '.jpeg'},                             'max_bytes': 5  * 1024 * 1024},
    'course-material':       {'exts': {'.pdf', '.ppt', '.pptx', '.doc', '.docx', '.md'},     'max_bytes': 50 * 1024 * 1024},
    'question-bank':         {'exts': {'.xlsx', '.xls', '.csv', '.json'},                    'max_bytes': 20 * 1024 * 1024},
    'assignment-attachment': {'exts': {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.zip'},    'max_bytes': 50 * 1024 * 1024},
    'knowledge-doc':         {'exts': {'.pdf', '.doc', '.docx', '.md', '.txt'},              'max_bytes': 100 * 1024 * 1024},
    'system-config':         {'exts': {'.json', '.yaml', '.yml'},                            'max_bytes': 5  * 1024 * 1024},
    'graph-data':            {'exts': {'.json', '.csv', '.xlsx'},                            'max_bytes': 20 * 1024 * 1024},
}

VALID_SCENES = set(SCENE_RESTRICTIONS.keys())


def _upload_root() -> Path:
    root = Path(current_app.instance_path) / 'uploads' / 'files'
    root.mkdir(parents=True, exist_ok=True)
    return root


class UploadValidationError(ValueError):
    pass


def _validate_content_signature(ext: str, data: bytes) -> None:
    if data.startswith(b'MZ'):
        raise UploadValidationError('file content does not match extension')
    if ext == '.pdf' and not data.startswith(b'%PDF'):
        raise UploadValidationError('invalid PDF signature')
    if ext == '.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise UploadValidationError('invalid PNG signature')
    if ext in {'.jpg', '.jpeg'} and not data.startswith(b'\xff\xd8\xff'):
        raise UploadValidationError('invalid JPEG signature')
    if ext in {'.docx', '.pptx', '.xlsx', '.zip'} and not data.startswith(b'PK'):
        raise UploadValidationError('invalid archive document signature')
    if ext == '.json':
        try:
            json.loads(data.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UploadValidationError('invalid JSON content') from exc


def validate_and_save(
    file: FileStorage,
    role: str,
    scene: str,
    user_id: int,
    related_id: str | None = None,
) -> dict:
    """
    校验并保存上传文件，返回 UploadResponse 字典。
    """
    # 1. 场景合法
    if scene not in VALID_SCENES:
        raise UploadValidationError(f'不支持的上传场景：{scene}')

    # 2. 角色权限
    allowed_roles = SCENE_ROLE_MATRIX.get(scene, [])
    if role not in allowed_roles:
        raise PermissionError(f'角色 {role} 不允许上传 {scene} 场景文件')

    # 3. 文件名 & 扩展名
    if not file or not file.filename:
        raise UploadValidationError('未选择文件')

    raw_filename = file.filename
    ext = ('.' + raw_filename.rsplit('.', 1)[-1].lower()) if '.' in raw_filename else ''

    if ext in BLOCKED_EXTENSIONS:
        raise UploadValidationError(f'禁止上传 {ext} 类型文件')

    restrictions = SCENE_RESTRICTIONS[scene]
    if ext not in restrictions['exts']:
        raise UploadValidationError(
            f'场景 {scene} 不允许 {ext} 文件，支持：{", ".join(sorted(restrictions["exts"]))}'
        )

    # 4. 读取数据并检查大小（避免流读取两次）
    data = file.read()
    if len(data) == 0:
        raise UploadValidationError('上传文件不能为空')
    if len(data) > restrictions['max_bytes']:
        mb = restrictions['max_bytes'] // (1024 * 1024)
        raise UploadValidationError(f'文件大小超过上限 {mb} MB')

    # 5. 存储
    _validate_content_signature(ext, data)

    uid = uuid.uuid4().hex[:16]
    safe_name = secure_filename(raw_filename)
    stored_name = f'{uid}_{safe_name}'
    dest_dir = _upload_root() / str(user_id) / scene
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / stored_name

    with open(dest_path, 'wb') as fh:
        fh.write(data)

    # 6. 构造响应
    url = f'/api/v1/uploads/files/{user_id}/{scene}/{stored_name}'
    return {
        'id':        uid,
        'fileName':  raw_filename,
        'fileType':  ext.lstrip('.') or 'bin',
        'fileSize':  len(data),
        'url':       url,
        'scene':     scene,
        'status':    'success',
        'createdAt': datetime.now(timezone.utc).isoformat(),
    }
