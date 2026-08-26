"""班级内师生文件共享（扫描 uploads/files 目录）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from app.models import Class, User, db
from app.utils.access import teacher_owns_class
from app.utils.time import utc_now

TEACHER_TO_STUDENT_SCENES = frozenset({'course-material', 'assignment-attachment'})
STUDENT_TO_TEACHER_SCENES = frozenset({'code-file', 'learning-report', 'screenshot'})


def _upload_root() -> Path:
    return Path(current_app.instance_path) / 'uploads' / 'files'


def _score_store_path() -> Path:
    return Path(current_app.instance_path) / 'uploads' / 'file_scores.json'


def _normalize_file_key(filepath: str) -> str:
    return (filepath or '').replace('\\', '/').lstrip('/')


def _load_scores() -> dict:
    path = _score_store_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_scores(payload: dict) -> None:
    path = _score_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _scan_user_files(user_id: int) -> list[dict]:
    base = _upload_root() / str(user_id)
    if not base.is_dir():
        return []
    items: list[dict] = []
    for scene_dir in base.iterdir():
        if not scene_dir.is_dir():
            continue
        scene = scene_dir.name
        for file_path in scene_dir.iterdir():
            if not file_path.is_file():
                continue
            stored_name = file_path.name
            display_name = stored_name.split('_', 1)[-1] if '_' in stored_name else stored_name
            stat = file_path.stat()
            created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            rel = f'{user_id}/{scene}/{stored_name}'
            items.append(
                {
                    'id': stored_name.split('_', 1)[0],
                    'fileName': display_name,
                    'fileType': file_path.suffix.lstrip('.') or 'bin',
                    'fileSize': stat.st_size,
                    'url': f'/api/v1/uploads/files/{rel}',
                    'scene': scene,
                    'owner_id': user_id,
                    'createdAt': created_at,
                }
            )
    return items


class ClassFileService:
    @staticmethod
    def list_incoming(user_id: int) -> dict:
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        role = user.role.name if user.role else ''
        items: list[dict] = []

        if role == 'student':
            if user.class_id:
                class_obj = db.session.get(Class, user.class_id)
                if class_obj:
                    teacher = db.session.get(User, class_obj.teacher_id)
                    for entry in _scan_user_files(class_obj.teacher_id):
                        if entry['scene'] in TEACHER_TO_STUDENT_SCENES:
                            items.append(
                                {
                                    **entry,
                                    'owner_name': (teacher.real_name or teacher.username) if teacher else '教师',
                                    'owner_username': teacher.username if teacher else None,
                                    'owner_role': 'teacher',
                                }
                            )
        elif role == 'teacher':
            class_ids = [c.id for c in Class.query.filter_by(teacher_id=user_id).all()]
            if class_ids:
                students = User.query.filter(User.class_id.in_(class_ids)).all()
                for student in students:
                    for entry in _scan_user_files(student.id):
                        if entry['scene'] in STUDENT_TO_TEACHER_SCENES:
                            items.append(
                                {
                                    **entry,
                                    'owner_name': student.real_name or student.username,
                                    'owner_username': student.username,
                                    'owner_role': 'student',
                                }
                            )
        elif role == 'admin':
            for entry in _scan_user_files(user_id):
                items.append({
                    **entry,
                    'owner_name': user.real_name or user.username,
                    'owner_username': user.username,
                    'owner_role': role,
                })

        scores = _load_scores()
        for item in items:
            rel = item['url'].replace('/api/v1/uploads/files/', '', 1)
            score_row = scores.get(rel)
            if isinstance(score_row, dict):
                item['score'] = score_row.get('score')
                item['scored_at'] = score_row.get('scored_at')
                item['scored_by'] = score_row.get('scored_by')
            else:
                item['score'] = None
                item['scored_at'] = None
                item['scored_by'] = None

        items.sort(key=lambda row: row.get('createdAt') or '', reverse=True)
        return {'items': items, 'class_id': user.class_id}

    @staticmethod
    def get_score(viewer_id: int, filepath: str) -> dict:
        key = _normalize_file_key(filepath)
        if not ClassFileService.can_access(viewer_id, key):
            raise PermissionError('无权查看该文件评分')
        row = _load_scores().get(key) or {}
        return {
            'filepath': key,
            'score': row.get('score'),
            'scored_at': row.get('scored_at'),
            'scored_by': row.get('scored_by'),
            'comment': row.get('comment') or '',
        }

    @staticmethod
    def set_score(teacher_id: int, filepath: str, score: int, comment: str | None = None) -> dict:
        key = _normalize_file_key(filepath)
        teacher = db.session.get(User, teacher_id)
        if not teacher or not teacher.role or teacher.role.name not in {'teacher', 'admin'}:
            raise PermissionError('仅教师可打分')
        if not ClassFileService.can_access(teacher_id, key):
            raise PermissionError('无权给该文件打分')

        try:
            value = int(score)
        except (TypeError, ValueError) as exc:
            raise ValueError('分数必须是 0–100 的整数') from exc
        if value < 0 or value > 100:
            raise ValueError('分数必须在 0–100 之间')

        store = _load_scores()
        store[key] = {
            'score': value,
            'scored_by': teacher_id,
            'scored_at': utc_now().isoformat(),
            'comment': (comment or '').strip()[:200],
        }
        _save_scores(store)
        return {
            'filepath': key,
            'score': value,
            'scored_at': store[key]['scored_at'],
            'scored_by': teacher_id,
            'comment': store[key]['comment'],
        }

    @staticmethod
    def can_access(viewer_id: int, filepath: str) -> bool:
        parts = filepath.split('/')
        if len(parts) < 3:
            return False

        try:
            owner_id = int(parts[0])
        except ValueError:
            return False

        scene = parts[1]
        if viewer_id == owner_id:
            return True

        viewer = db.session.get(User, viewer_id)
        owner = db.session.get(User, owner_id)
        if not viewer or not owner or not viewer.role or not owner.role:
            return False

        if viewer.role.name == 'admin':
            return True

        if viewer.role.name == 'student' and owner.role.name == 'teacher':
            if scene not in TEACHER_TO_STUDENT_SCENES:
                return False
            if not viewer.class_id:
                return False
            class_obj = db.session.get(Class, viewer.class_id)
            return bool(class_obj and class_obj.teacher_id == owner_id)

        if viewer.role.name == 'teacher' and owner.role.name == 'student':
            if scene not in STUDENT_TO_TEACHER_SCENES:
                return False
            if not owner.class_id:
                return False
            return teacher_owns_class(viewer, owner.class_id)

        return False
