# -*- coding: utf-8 -*-
"""Knowledge Intelligence Layer：知识库文档 / 知识图谱 / 索引状态 / 使用分析 路由。

Controller 只做参数校验与权限判断，业务全部委托 IndexService / GraphService / KnowledgeService。
"""
from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models.knowledge_document import KNOWLEDGE_TYPES, RESOURCE_TYPES
from ..models.knowledge_graph import NODE_TYPES, RELATION_TYPES
from ..services.knowledge import KnowledgeService
from ..services.knowledge.analytics_service import KnowledgeAnalyticsService
from ..services.knowledge.graph_service import GraphService, GraphValidationError
from ..services.knowledge.index_service import DocumentValidationError, IndexService
from ..utils.access import current_user_from_id
from ..utils.decorators import role_required
from ..utils.response import error_response, paginated_response, success_response

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/api/v1/knowledge')

_STAFF = ('teacher', 'admin')


def _uid() -> int:
    return int(get_jwt_identity())


def _bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _int(value, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(',') if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


# ---------------------------------------------------------------------- documents
@knowledge_bp.post('/documents')
@jwt_required()
@role_required(*_STAFF)
def upload_document():
    """multipart 上传文档，或 JSON 直接提交文本（title + text）。"""
    user_id = _uid()
    file = request.files.get('file')
    try:
        if file is not None:
            form = request.form
            resource_type = form.get('resource_type') or 'textbook'
            if resource_type not in RESOURCE_TYPES:
                return error_response('resource_type 非法', 40001, {'allowed': list(RESOURCE_TYPES)}, 400)
            doc = IndexService.register_upload(
                file,
                user_id=user_id,
                title=(form.get('title') or '').strip() or None,
                course_id=(form.get('course_id') or '').strip() or None,
                chapter=(form.get('chapter') or '').strip(),
                resource_type=resource_type,
                audience_level=form.get('audience_level') or 'beginner',
                teacher_verified=_bool(form.get('teacher_verified')),
                concept_hints=_list(form.get('concept_ids')),
                auto_index=_bool(form.get('auto_index'), True),
            )
        else:
            body = request.get_json(silent=True) or {}
            title = (body.get('title') or '').strip()
            text = body.get('text') or body.get('content') or ''
            if not title:
                return error_response('title 不能为空', 40001, None, 400)
            resource_type = body.get('resource_type') or 'markdown'
            if resource_type not in RESOURCE_TYPES:
                return error_response('resource_type 非法', 40001, {'allowed': list(RESOURCE_TYPES)}, 400)
            doc = IndexService.register_text(
                title=title,
                text=text,
                user_id=user_id,
                course_id=(body.get('course_id') or '').strip() or None,
                chapter=(body.get('chapter') or '').strip(),
                resource_type=resource_type,
                audience_level=body.get('audience_level') or 'beginner',
                source=body.get('source') or 'manual',
                teacher_verified=_bool(body.get('teacher_verified')),
                concept_hints=_list(body.get('concept_ids')),
                meta=body.get('meta') if isinstance(body.get('meta'), dict) else None,
                auto_index=_bool(body.get('auto_index'), True),
            )
    except DocumentValidationError as exc:
        return error_response(str(exc), 40001, None, 400)
    except ValueError as exc:  # 文件签名校验失败等
        return error_response(str(exc), 40001, None, 400)
    payload = doc.to_dict()
    job = IndexService.latest_job(doc.id)
    payload['job'] = job.to_dict() if job else None
    return success_response(payload, '文档已登记', status_code=201)


@knowledge_bp.get('/documents')
@jwt_required()
@role_required(*_STAFF)
def list_documents():
    args = request.args
    page = _int(args.get('page'), 1, 1, 10_000)
    per_page = _int(args.get('per_page') or args.get('limit'), 20, 1, 100)
    pagination = IndexService.list_documents(
        status=(args.get('status') or '').strip().upper() or None,
        course_id=(args.get('course_id') or '').strip() or None,
        source=(args.get('source') or '').strip() or None,
        keyword=(args.get('keyword') or args.get('q') or '').strip() or None,
        page=page,
        per_page=per_page,
    )
    return paginated_response([d.to_dict() for d in pagination.items], pagination.total, page, per_page)


@knowledge_bp.get('/documents/<string:document_id>')
@jwt_required()
@role_required(*_STAFF)
def get_document(document_id: str):
    from ..models import KnowledgeDocument, db

    doc = db.session.get(KnowledgeDocument, document_id)
    if not doc:
        return error_response('文档不存在', 40401, None, 404)
    payload = doc.to_dict()
    job = IndexService.latest_job(document_id)
    payload['job'] = job.to_dict() if job else None
    return success_response(payload)


@knowledge_bp.patch('/documents/<string:document_id>')
@jwt_required()
@role_required(*_STAFF)
def update_document(document_id: str):
    body = request.get_json(silent=True) or {}
    if 'resource_type' in body and body['resource_type'] not in RESOURCE_TYPES:
        return error_response('resource_type 非法', 40001, {'allowed': list(RESOURCE_TYPES)}, 400)
    doc = IndexService.update_document(
        document_id,
        title=(body.get('title') or '').strip() or None,
        chapter=body.get('chapter'),
        resource_type=body.get('resource_type'),
        audience_level=body.get('audience_level'),
        quality_score=body.get('quality_score'),
        course_id=body.get('course_id'),
    )
    if not doc:
        return error_response('文档不存在', 40401, None, 404)
    return success_response(doc.to_dict(), '文档已更新')


@knowledge_bp.post('/documents/<string:document_id>/index')
@jwt_required()
@role_required(*_STAFF)
def index_document(document_id: str):
    """触发（重新）索引：version+1，异步执行，前端轮询 GET /documents/{id}。"""
    try:
        job = IndexService.start_index(document_id, user_id=_uid())
    except DocumentValidationError as exc:
        return error_response(str(exc), 40401, None, 404)
    return success_response(job.to_dict(), '索引任务已提交', status_code=202)


@knowledge_bp.post('/documents/<string:document_id>/verify')
@jwt_required()
@role_required(*_STAFF)
def verify_document(document_id: str):
    body = request.get_json(silent=True) or {}
    doc = IndexService.verify_document(
        document_id,
        user_id=_uid(),
        verified=_bool(body.get('verified'), True),
        quality_score=body.get('quality_score'),
    )
    if not doc:
        return error_response('文档不存在', 40401, None, 404)
    return success_response(doc.to_dict(), '审核状态已更新')


@knowledge_bp.get('/documents/<string:document_id>/chunks')
@jwt_required()
@role_required(*_STAFF)
def list_chunks(document_id: str):
    args = request.args
    page = _int(args.get('page'), 1, 1, 10_000)
    per_page = _int(args.get('per_page') or args.get('limit'), 50, 1, 200)
    knowledge_type = (args.get('knowledge_type') or '').strip() or None
    if knowledge_type and knowledge_type not in KNOWLEDGE_TYPES:
        return error_response('knowledge_type 非法', 40001, {'allowed': list(KNOWLEDGE_TYPES)}, 400)
    pagination = IndexService.list_chunks(document_id, page=page, per_page=per_page, knowledge_type=knowledge_type)
    include_content = _bool(args.get('include_content'), True)
    items = [c.to_dict(include_content=include_content, preview_chars=None if include_content else 200) for c in pagination.items]
    return paginated_response(items, pagination.total, page, per_page)


@knowledge_bp.delete('/documents/<string:document_id>')
@jwt_required()
@role_required('admin')
def delete_document(document_id: str):
    if not IndexService.delete_document(document_id):
        return error_response('文档不存在', 40401, None, 404)
    return success_response(None, '文档已删除')


# ---------------------------------------------------------------------- index status
@knowledge_bp.get('/index/status')
@jwt_required()
@role_required(*_STAFF)
def index_status():
    return success_response(KnowledgeService.status())


@knowledge_bp.post('/seed')
@jwt_required()
@role_required('admin')
def seed_knowledge():
    """管理员手动重建图谱种子 / 注册内建课程文档（幂等）。"""
    body = request.get_json(silent=True) or {}
    report = KnowledgeService.ensure_ready(
        seed_graph=_bool(body.get('seed_graph'), True),
        index_builtin=_bool(body.get('index_builtin'), True),
    )
    return success_response(report, '初始化完成')


# ---------------------------------------------------------------------- graph
@knowledge_bp.get('/graph')
@jwt_required()
def get_graph():
    args = request.args
    node_types = _list(args.get('node_types'))
    if any(t not in NODE_TYPES for t in node_types):
        return error_response('node_types 非法', 40001, {'allowed': list(NODE_TYPES)}, 400)
    relation_types = _list(args.get('relation_types'))
    if any(t not in RELATION_TYPES for t in relation_types):
        return error_response('relation_types 非法', 40001, {'allowed': list(RELATION_TYPES)}, 400)
    payload = GraphService.get_graph(
        course_id=(args.get('course_id') or '').strip() or None,
        node_types=node_types or None,
        relation_types=relation_types or None,
        include_problem_nodes=_bool(args.get('include_problems')),
    )
    return success_response(payload)


@knowledge_bp.get('/concepts')
@jwt_required()
def list_concepts():
    args = request.args
    node_types = _list(args.get('node_types')) or ['concept', 'skill']
    if any(t not in NODE_TYPES for t in node_types):
        return error_response('node_types 非法', 40001, {'allowed': list(NODE_TYPES)}, 400)
    rows = GraphService.list_concepts(
        course_id=(args.get('course_id') or '').strip() or None,
        node_types=node_types,
        chapter=(args.get('chapter') or '').strip() or None,
        keyword=(args.get('keyword') or args.get('q') or '').strip() or None,
    )
    return success_response({'items': [r.to_dict() for r in rows], 'total': len(rows)})


@knowledge_bp.get('/concepts/<path:concept_id>')
@jwt_required()
def get_concept(concept_id: str):
    payload = KnowledgeService.concept_detail(concept_id)
    if not payload:
        return error_response('知识点不存在', 40401, None, 404)
    if _bool(request.args.get('with_usage')):
        user = current_user_from_id(_uid())
        if user and user.role and user.role.name in _STAFF:
            payload['usage'] = KnowledgeAnalyticsService.concept_usage(concept_id)
    return success_response(payload)


@knowledge_bp.patch('/concepts/<path:concept_id>')
@jwt_required()
@role_required(*_STAFF)
def update_concept(concept_id: str):
    body = request.get_json(silent=True) or {}
    try:
        row = GraphService.update_concept(concept_id, **body)
    except GraphValidationError as exc:
        return error_response(str(exc), 40001, None, 400)
    if not row:
        return error_response('知识点不存在', 40401, None, 404)
    return success_response(row.to_dict(expand=True), '知识点已更新')


@knowledge_bp.get('/concepts/<path:concept_id>/knowledge')
@jwt_required()
def concept_knowledge(concept_id: str):
    """按知识点取 grounded 材料（供教师查看“AI 会使用哪些资源”、学生查看参考知识）。"""
    args = request.args
    knowledge_types = _list(args.get('knowledge_types'))
    if any(t not in KNOWLEDGE_TYPES for t in knowledge_types):
        return error_response('knowledge_types 非法', 40001, {'allowed': list(KNOWLEDGE_TYPES)}, 400)
    payload = KnowledgeService.concept_knowledge(
        [concept_id],
        user_id=_uid(),
        knowledge_types=knowledge_types or None,
        top_k=_int(args.get('top_k'), 4, 1, 12),
    )
    if not payload['concept_ids']:
        return error_response('知识点不存在', 40401, None, 404)
    return success_response(payload)


@knowledge_bp.post('/relations')
@jwt_required()
@role_required(*_STAFF)
def add_relation():
    body = request.get_json(silent=True) or {}
    source_id = (body.get('source_id') or '').strip()
    target_id = (body.get('target_id') or '').strip()
    relation_type = (body.get('relation_type') or '').strip().upper()
    if not source_id or not target_id or not relation_type:
        return error_response('source_id / target_id / relation_type 必填', 40001, None, 400)
    user = current_user_from_id(_uid())
    try:
        row = GraphService.add_relation(
            source_id,
            target_id,
            relation_type,
            weight=float(body.get('weight') or 1.0),
            source='teacher' if user and user.role and user.role.name == 'teacher' else 'manual',
            teacher_verified=_bool(body.get('teacher_verified'), True),
            verified_by=_uid(),
            note=body.get('note'),
            commit=True,
        )
    except GraphValidationError as exc:
        return error_response(str(exc), 40001, None, 400)
    except (TypeError, ValueError):
        return error_response('weight 必须为数字', 40001, None, 400)
    return success_response(row.to_dict(), '关系已保存', status_code=201)


@knowledge_bp.post('/relations/<int:relation_id>/verify')
@jwt_required()
@role_required(*_STAFF)
def verify_relation(relation_id: int):
    body = request.get_json(silent=True) or {}
    row = GraphService.verify_relation(relation_id, _uid(), verified=_bool(body.get('verified'), True))
    if not row:
        return error_response('关系不存在', 40401, None, 404)
    return success_response(row.to_dict(), '关系审核状态已更新')


@knowledge_bp.delete('/relations/<int:relation_id>')
@jwt_required()
@role_required(*_STAFF)
def delete_relation(relation_id: int):
    if not GraphService.remove_relation(relation_id):
        return error_response('关系不存在', 40401, None, 404)
    return success_response(None, '关系已删除')


# ---------------------------------------------------------------------- analytics
@knowledge_bp.get('/analytics/overview')
@jwt_required()
@role_required(*_STAFF)
def analytics_overview():
    args = request.args
    user = current_user_from_id(_uid())
    is_teacher = bool(user and user.role and user.role.name == 'teacher')
    payload = KnowledgeAnalyticsService.overview(
        days=_int(args.get('days'), 14, 1, 180),
        class_id=args.get('class_id', type=int),
        teacher_id=user.id if is_teacher else None,  # 教师只统计自己名下班级
        limit=_int(args.get('limit'), 10, 1, 50),
    )
    return success_response(payload)


@knowledge_bp.get('/analytics/queries')
@jwt_required()
@role_required('admin')
def analytics_queries():
    args = request.args
    page = _int(args.get('page'), 1, 1, 10_000)
    per_page = _int(args.get('per_page') or args.get('limit'), 20, 1, 100)
    pagination = KnowledgeAnalyticsService.recent_logs(
        page=page,
        per_page=per_page,
        user_id=args.get('user_id', type=int),
        scene=(args.get('scene') or '').strip() or None,
        status=(args.get('status') or '').strip() or None,
    )
    return paginated_response([r.to_dict() for r in pagination.items], pagination.total, page, per_page)
