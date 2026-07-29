# -*- coding: utf-8 -*-
"""Knowledge graph API."""
from urllib.parse import unquote

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.knowledge_graph import KnowledgeGraphService
from ..utils.response import error_response, success_response

kg_graph_bp = Blueprint('knowledge_graph', __name__, url_prefix='/api/v1/knowledge-graph')


@kg_graph_bp.get('/student')
@jwt_required()
def student_graph():
    user_id = int(get_jwt_identity())
    return success_response(KnowledgeGraphService.get_student_graph(user_id))


@kg_graph_bp.get('/student/<int:student_id>')
@jwt_required()
def student_graph_for_teacher(student_id: int):
    return success_response(KnowledgeGraphService.get_student_graph(student_id))


@kg_graph_bp.get('/class/<int:class_id>')
@jwt_required()
def class_graph(class_id: int):
    try:
        return success_response(KnowledgeGraphService.get_class_graph(class_id))
    except Exception as exc:
        return error_response(str(exc), 40001, None, 400)


def _affected_students_payload(class_id: int, node_id: str):
    cleaned = unquote((node_id or '').strip())
    if not cleaned:
        raise ValueError('缺少知识点 node_id')
    return KnowledgeGraphService.get_node_affected_students(class_id, cleaned)


@kg_graph_bp.get('/class/<int:class_id>/affected-students')
@jwt_required()
def class_node_affected_students_query(class_id: int):
    """Query-param 形式，避免 path 编码/代理导致的 404。"""
    try:
        node_id = (request.args.get('node_id') or '').strip()
        return success_response(_affected_students_payload(class_id, node_id))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@kg_graph_bp.get('/class/<int:class_id>/nodes/<path:node_id>/students')
@jwt_required()
def class_node_affected_students(class_id: int, node_id: str):
    try:
        return success_response(_affected_students_payload(class_id, node_id))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@kg_graph_bp.get('/admin')
@jwt_required()
def admin_graph():
    return success_response(KnowledgeGraphService.get_admin_graph())


