# -*- coding: utf-8 -*-
"""Knowledge graph API."""
from flask import Blueprint
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
        return error_response(str(exc), code=400)


@kg_graph_bp.get('/admin')
@jwt_required()
def admin_graph():
    return success_response(KnowledgeGraphService.get_admin_graph())


