# -*- coding: utf-8 -*-
"""Graph-enhanced RAG 路由：问答 / 仅检索 / 来源查看 / 请求日志。

- 学生端 /rag/query 只返回安全视图（不含 embedding / similarity / rerank 分值）；
- debug=true 仅管理员生效；
- 所有业务委托 KnowledgeService。
"""
from __future__ import annotations

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models import KnowledgeChunk, KnowledgeDocument, RagQueryLog, db
from ..models.knowledge_document import KNOWLEDGE_TYPES
from ..services.knowledge import KnowledgeService
from ..services.knowledge.analytics_service import KnowledgeAnalyticsService
from ..utils.access import current_user_from_id, is_admin
from ..utils.decorators import role_required
from ..utils.response import error_response, paginated_response, success_response

rag_bp = Blueprint('rag', __name__, url_prefix='/api/v1/rag')

_MAX_QUERY_CHARS = 2000
_ALLOWED_SCENES = {'chat', 'trial', 'practice', 'exercise', 'emergency', 'problem', 'diagnosis', 'path', 'resource'}


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


def _actor():
    user = current_user_from_id(_uid())
    role = user.role.name if user and user.role else 'student'
    return user, role


def _context(body: dict) -> dict:
    """只透传白名单字段，避免前端注入任意上下文。"""
    raw = body.get('context') if isinstance(body.get('context'), dict) else {}
    ctx: dict = {}
    for key in ('task_type', 'task_id', 'trial_id', 'problem_id', 'concept_hint', 'concept_ids', 'stage', 'title'):
        if key in raw and raw[key] not in (None, ''):
            ctx[key] = raw[key]
    for key in ('task_type', 'concept_hint', 'hint_level', 'problem_id', 'trial_id'):
        if key in body and body[key] not in (None, ''):
            ctx[key] = body[key]
    if 'hint_level' in ctx:
        ctx['hint_level'] = _int(ctx['hint_level'], 1, 1, 4)
    return ctx


@rag_bp.post('/query')
@jwt_required()
def rag_query():
    body = request.get_json(silent=True) or {}
    query = (body.get('query') or body.get('question') or '').strip()
    if not query:
        return error_response('query 不能为空', 40001, None, 400)
    if len(query) > _MAX_QUERY_CHARS:
        return error_response(f'query 超过 {_MAX_QUERY_CHARS} 字上限', 40001, None, 400)
    user, role = _actor()
    scene = (body.get('scene') or 'chat').strip().lower()
    if scene not in _ALLOWED_SCENES:
        scene = 'chat'
    debug = _bool(body.get('debug')) and is_admin(user)
    history = body.get('history') if isinstance(body.get('history'), list) else None
    if history:
        history = [
            {'role': str(h.get('role', 'user'))[:16], 'content': str(h.get('content', ''))[:_MAX_QUERY_CHARS]}
            for h in history[-6:]
            if isinstance(h, dict) and h.get('content')
        ]
    use_llm = body.get('use_llm') if is_admin(user) and isinstance(body.get('use_llm'), bool) else None
    answer = KnowledgeService.answer(
        query,
        user_id=user.id if user else None,
        role=role,
        scene=scene,
        context=_context(body),
        history=history,
        debug=debug,
        use_llm=use_llm,
    )
    return success_response(answer.to_dict(include_debug=debug))


@rag_bp.post('/retrieve')
@jwt_required()
@role_required('teacher', 'admin')
def rag_retrieve():
    """仅检索（管理员检索测试 / 教师查看取材），返回完整调试信息。"""
    body = request.get_json(silent=True) or {}
    query = (body.get('query') or '').strip()
    if not query:
        return error_response('query 不能为空', 40001, None, 400)
    if len(query) > _MAX_QUERY_CHARS:
        return error_response(f'query 超过 {_MAX_QUERY_CHARS} 字上限', 40001, None, 400)
    knowledge_types = body.get('knowledge_types') if isinstance(body.get('knowledge_types'), list) else None
    if knowledge_types and any(t not in KNOWLEDGE_TYPES for t in knowledge_types):
        return error_response('knowledge_types 非法', 40001, {'allowed': list(KNOWLEDGE_TYPES)}, 400)
    document_ids = body.get('document_ids') if isinstance(body.get('document_ids'), list) else None
    user, role = _actor()
    # 允许以指定学生视角检索（教师/管理员调试学习者上下文），默认以自己为学习者
    as_user = body.get('as_user_id')
    learner_id = int(as_user) if isinstance(as_user, int) or (isinstance(as_user, str) and as_user.isdigit()) else (user.id if user else None)
    payload = KnowledgeService.retrieve(
        query,
        user_id=learner_id,
        role='student' if as_user else role,
        context=_context(body),
        top_k=_int(body.get('top_k'), 6, 1, 20) if body.get('top_k') is not None else None,
        knowledge_types=knowledge_types,
        document_ids=[str(d) for d in document_ids][:20] if document_ids else None,
        require_verified=_bool(body.get('require_verified')),
        log=_bool(body.get('log'), True),
    )
    return success_response(payload)


@rag_bp.get('/sources/<string:chunk_id>')
@jwt_required()
def rag_source(chunk_id: str):
    """查看某条来源（chunk）的原文。学生只看安全字段，教师/管理员可看完整元数据。"""
    chunk = db.session.get(KnowledgeChunk, chunk_id)
    if not chunk or chunk.status != 'active':
        return error_response('来源不存在', 40401, None, 404)
    user, role = _actor()
    doc = db.session.get(KnowledgeDocument, chunk.document_id)
    if role in ('teacher', 'admin'):
        payload = chunk.to_dict(include_content=True)
        payload['document'] = doc.to_dict() if doc else None
    else:
        payload = {
            'chunk_id': chunk.chunk_id,
            'document_id': chunk.document_id,
            'title': chunk.title or (doc.title if doc else ''),
            'document_title': doc.title if doc else '',
            'knowledge_type': chunk.knowledge_type,
            'concept_ids': list(chunk.concept_ids or []),
            'resource_type': chunk.resource_type,
            'source': chunk.source,
            'source_page': chunk.source_page,
            'teacher_verified': bool(chunk.teacher_verified),
            'content': chunk.content,
        }
    return success_response(payload)


@rag_bp.get('/logs')
@jwt_required()
@role_required('admin')
def rag_logs():
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


@rag_bp.get('/logs/<int:log_id>')
@jwt_required()
@role_required('admin')
def rag_log_detail(log_id: int):
    row = db.session.get(RagQueryLog, log_id)
    if not row:
        return error_response('日志不存在', 40401, None, 404)
    return success_response(row.to_dict())
