# -*- coding: utf-8 -*-
"""统一资料上传接口 POST /api/v1/upload 及文件服务 GET /api/v1/uploads/files/…。"""
from pathlib import Path

from flask import Blueprint, current_app, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User, db
from app.services.class_files import ClassFileService
from app.services.file_upload import UploadValidationError, validate_and_save
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

upload_bp = Blueprint('upload', __name__, url_prefix='/api/v1')


@upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """三端结构化文件上传。"""
    try:
        user_id = int(get_jwt_identity())
        user = db.session.get(User, user_id)
        if not user:
            return error_response('用户不存在', 40401, None, 404)

        role = request.form.get('role', '').strip()
        scene = request.form.get('scene', '').strip()
        related_id = request.form.get('relatedId') or None
        file = request.files.get('file')

        if not role or not scene:
            return error_response('role 和 scene 不能为空', 40001, None, 400)

        # JWT 角色必须与请求 role 一致
        actual_role = user.role.name if user.role else ''
        if actual_role != role:
            return error_response(
                f'当前账号角色为 {actual_role}，不能使用 {role} 上传', 40301, None, 403
            )

        result = validate_and_save(file, role, scene, user_id, related_id)
        return success_response(result, '上传成功')

    except UploadValidationError as exc:
        return error_response(str(exc), 40001, None, 400)
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@upload_bp.route('/uploads/files/<path:filepath>', methods=['GET'])
@jwt_required()
def serve_upload_file(filepath: str):
    """下载/预览上传文件（本人文件；admin 可访问所有）。"""
    try:
        user_id = int(get_jwt_identity())
        user = db.session.get(User, user_id)
        if not user:
            return error_response('用户不存在', 40401, None, 404)

        actual_role = user.role.name if user.role else ''
        if actual_role != 'admin' and not ClassFileService.can_access(user_id, filepath):
            return error_response('无权访问该文件', 40301, None, 403)

        base = Path(current_app.instance_path) / 'uploads' / 'files'
        target = (base / filepath).resolve()
        if not str(target).startswith(str(base.resolve())):
            return error_response('非法路径', 40001, None, 400)

        if not target.is_file():
            return error_response('文件不存在', 40401, None, 404)

        return send_from_directory(base, filepath)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@upload_bp.route('/class-files', methods=['GET'])
@jwt_required()
def list_class_files():
    """列出当前用户可接收的班级共享文件。"""
    try:
        user_id = int(get_jwt_identity())
        payload = ClassFileService.list_incoming(user_id)
        return success_response(payload)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@upload_bp.route('/class-files/score', methods=['GET'])
@jwt_required()
def get_class_file_score():
    """读取班级提交文件评分。"""
    try:
        user_id = int(get_jwt_identity())
        filepath = (request.args.get('filepath') or '').strip()
        if not filepath:
            return error_response('缺少 filepath', 40001, None, 400)
        return success_response(ClassFileService.get_score(user_id, filepath))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@upload_bp.route('/class-files/score', methods=['PUT', 'POST'])
@jwt_required()
@role_required('teacher', 'admin')
def set_class_file_score():
    """教师给班级提交文件打分（0–100）。"""
    try:
        user_id = int(get_jwt_identity())
        body = request.get_json(silent=True) or {}
        filepath = (body.get('filepath') or request.args.get('filepath') or '').strip()
        if not filepath:
            return error_response('缺少 filepath', 40001, None, 400)
        score = body.get('score')
        comment = body.get('comment')
        return success_response(
            ClassFileService.set_score(user_id, filepath, score, comment),
            '评分已保存',
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


# ─── 后续处理 stub 路由 ────────────────────────────────────────

@upload_bp.post('/graph/import')
@jwt_required()
@role_required('admin')
def import_graph_data():
    """stub：导入知识图谱数据（第一阶段 pending）。"""
    body = request.get_json(silent=True) or {}
    file_id = body.get('fileId', '')
    return success_response({'status': 'pending', 'fileId': file_id, 'message': '图谱导入队列已接收，功能即将开放'})


@upload_bp.post('/config/validate')
@jwt_required()
@role_required('admin')
def validate_config():
    """stub：验证系统配置文件（第一阶段 pending）。"""
    body = request.get_json(silent=True) or {}
    file_id = body.get('fileId', '')
    return success_response({'status': 'pending', 'fileId': file_id, 'message': '配置校验队列已接收，功能即将开放'})


@upload_bp.post('/questions/import')
@jwt_required()
@role_required('teacher', 'admin')
def import_questions():
    """stub：批量导入题库文件（第一阶段 pending）。"""
    body = request.get_json(silent=True) or {}
    file_id = body.get('fileId', '')
    return success_response({'status': 'pending', 'fileId': file_id, 'message': '题库导入队列已接收，功能即将开放'})
