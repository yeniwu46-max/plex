"""班级内师生文件共享（扫描 uploads/files 目录）。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from app.models import Class, User, db
from app.utils.access import teacher_owns_class

TEACHER_TO_STUDENT_SCENES = frozenset({'course-material', 'assignment-attachment'})
STUDENT_TO_TEACHER_SCENES = frozenset({'code-file', 'learning-report', 'screenshot'})


def _upload_root() -> Path:
    return Path(current_app.instance_path) / 'uploads' / 'files'


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
                                    'owner_role': 'student',
                                }
                            )
        elif role == 'admin':
            for entry in _scan_user_files(user_id):
                items.append({**entry, 'owner_name': user.real_name or user.username, 'owner_role': role})

        items.sort(key=lambda row: row.get('createdAt') or '', reverse=True)
        return {'items': items, 'class_id': user.class_id}

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
