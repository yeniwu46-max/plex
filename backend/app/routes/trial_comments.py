"""试炼题目评论路由。"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.trial_comment import TrialCommentService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

trial_comments_bp = Blueprint('trial_comments', __name__, url_prefix='/api/v1/trial-comments')


@trial_comments_bp.route('', methods=['GET'])
@jwt_required()
def list_comments():
    try:
        question_ref = request.args.get('question_ref', '').strip()
        viewer_id = int(get_jwt_identity())
        items = TrialCommentService.list_for_question(question_ref, viewer_id)
        return success_response({'items': items})
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trial_comments_bp.route('', methods=['POST'])
@jwt_required()
@role_required('student', 'teacher', 'admin')
def create_comment():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True)
        if not data:
            return error_response('请求体必须是 JSON 格式', 40004, None, 400)
        row = TrialCommentService.create(
            user_id,
            data.get('question_ref'),
            data.get('content'),
            parent_id=data.get('parent_id'),
        )
        return success_response(row, '评论已发布', 0, 201)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@trial_comments_bp.route('/<int:comment_id>/like', methods=['POST'])
@jwt_required()
@role_required('student', 'teacher', 'admin')
def toggle_like(comment_id: int):
    try:
        user_id = int(get_jwt_identity())
        result = TrialCommentService.toggle_like(user_id, comment_id)
        return success_response(result)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
