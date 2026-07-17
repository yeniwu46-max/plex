"""学生入班申请路由。"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User, db
from app.services.class_enrollment import ClassEnrollmentService
from app.utils.access import is_admin
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

class_enrollments_bp = Blueprint('class_enrollments', __name__, url_prefix='/api/v1/class-enrollments')


@class_enrollments_bp.route('/lookup', methods=['POST'])
@jwt_required()
@role_required('student')
def lookup_class_by_code():
    try:
        data = request.get_json() or {}
        join_code = data.get('join_code')
        if not join_code:
            return error_response('缺少班级编号', 40001, None, 400)
        result = ClassEnrollmentService.lookup_class(join_code)
        return success_response(result)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@class_enrollments_bp.route('/apply', methods=['POST'])
@jwt_required()
@role_required('student')
def apply_to_class():
    try:
        student_id = int(get_jwt_identity())
        data = request.get_json() or {}
        join_code = data.get('join_code')
        if not join_code:
            return error_response('缺少班级编号', 40001, None, 400)
        message = data.get('message')
        row = ClassEnrollmentService.apply(student_id, join_code, message)
        return success_response(row.to_dict(), '入班申请已提交，请等待教师审核', 0, 201)
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@class_enrollments_bp.route('/mine', methods=['GET'])
@jwt_required()
@role_required('student')
def list_my_enrollment_requests():
    try:
        student_id = int(get_jwt_identity())
        status = request.args.get('status')
        rows = ClassEnrollmentService.list_for_student(student_id, status=status)
        return success_response(rows)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@class_enrollments_bp.route('', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_enrollment_requests():
    try:
        user_id = int(get_jwt_identity())
        user = db.session.get(User, user_id)
        status = request.args.get('status')
        class_id = request.args.get('class_id', type=int)

        if is_admin(user):
            rows = ClassEnrollmentService.list_for_admin(status=status, class_id=class_id)
        else:
            rows = ClassEnrollmentService.list_for_teacher(user_id, status=status, class_id=class_id)
        return success_response(rows)
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@class_enrollments_bp.route('/<int:request_id>/review', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def review_enrollment_request(request_id):
    try:
        reviewer_id = int(get_jwt_identity())
        data = request.get_json() or {}
        approve = bool(data.get('approve'))
        note = data.get('note')
        row = ClassEnrollmentService.review(request_id, reviewer_id, approve, note)
        label = '已通过' if row.status == 'approved' else '已驳回'
        return success_response(row.to_dict(), f'申请{label}')
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
