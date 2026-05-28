"""班级变更审批路由。"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.class_request import ClassRequestService
from app.utils.access import is_admin
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

class_requests_bp = Blueprint('class_requests', __name__, url_prefix='/api/v1/class-requests')


@class_requests_bp.route('', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_class_requests():
    try:
        from app.models import User

        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        status = request.args.get('status')
        if is_admin(user):
            rows = ClassRequestService.list_requests(status=status)
        else:
            rows = ClassRequestService.list_requests(status=status, requester_id=user_id)
        return success_response(rows)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@class_requests_bp.route('', methods=['POST'])
@jwt_required()
@role_required('teacher')
def submit_class_request():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        action = data.get('action')
        class_id = data.get('class_id', type=int) if data.get('class_id') is not None else None
        payload = data.get('payload') or {}
        reason = data.get('reason')
        row = ClassRequestService.create_request(user_id, action, payload, class_id=class_id, reason=reason)
        return success_response(row.to_dict(), '申请已提交，等待管理员审核', 0, 201)
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@class_requests_bp.route('/<int:request_id>/review', methods=['POST'])
@jwt_required()
@role_required('admin')
def review_class_request(request_id):
    try:
        reviewer_id = int(get_jwt_identity())
        data = request.get_json() or {}
        approve = bool(data.get('approve'))
        note = data.get('note')
        row = ClassRequestService.review(request_id, reviewer_id, approve, note)
        label = '已通过' if row.status == 'approved' else '已驳回'
        return success_response(row.to_dict(), f'申请{label}')
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
