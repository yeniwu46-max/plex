"""全局搜索路由 — GET /api/v1/search"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User, db
from app.utils.response import success_response, error_response
from ..services.search import search_items, SCOPE_CATEGORIES

search_bp = Blueprint('search', __name__, url_prefix='/api/v1/search')

ROLE_SCOPE_MAP = {
    'student': ['student'],
    'teacher': ['teacher', 'student'],
    'admin': ['student', 'teacher', 'admin'],
}


@search_bp.route('', methods=['GET'])
@jwt_required()
def global_search():
    q = request.args.get('q', '').strip()
    scope = request.args.get('scope', '')
    try:
        limit = int(request.args.get('limit', 20))
    except ValueError:
        limit = 20

    if not scope or scope not in SCOPE_CATEGORIES:
        return error_response('scope 参数无效，应为 student/teacher/admin', 400, None, 400)

    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    role = user.role.name if user and user.role else 'student'

    allowed_scopes = ROLE_SCOPE_MAP.get(role, ['student'])
    if scope not in allowed_scopes:
        return error_response('无权访问该搜索范围', 403, None, 403)

    groups = search_items(q, scope, limit=min(limit, 50))
    return success_response({'groups': groups})
