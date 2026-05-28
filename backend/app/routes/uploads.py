"""文件上传（头像等）。"""
import os
import uuid
from pathlib import Path

from flask import Blueprint, current_app, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from app.models import User, db
from app.utils.response import error_response, success_response

uploads_bp = Blueprint('uploads', __name__, url_prefix='/api/v1/uploads')

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_BYTES = 2 * 1024 * 1024


def _upload_root() -> Path:
    root = Path(current_app.instance_path) / 'uploads' / 'avatars'
    root.mkdir(parents=True, exist_ok=True)
    return root


@uploads_bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    try:
        file = request.files.get('file')
        if not file or not file.filename:
            return error_response('请选择图片文件', 40001, None, 400)

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXT:
            return error_response('仅支持 png/jpg/jpeg/gif/webp', 40001, None, 400)

        raw = file.read()
        if len(raw) > MAX_BYTES:
            return error_response('图片不能超过 2MB', 40001, None, 400)

        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return error_response('用户不存在', 40401, None, 404)

        filename = secure_filename(f'{user_id}_{uuid.uuid4().hex[:12]}.{ext}')
        path = _upload_root() / filename
        with open(path, 'wb') as handle:
            handle.write(raw)

        avatar_url = f'/api/v1/uploads/avatars/{filename}'
        user.avatar_url = avatar_url
        db.session.commit()

        return success_response({'avatar_url': avatar_url}, '头像已更新')
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@uploads_bp.route('/avatars/<path:filename>', methods=['GET'])
def serve_avatar(filename):
    return send_from_directory(_upload_root(), filename)
