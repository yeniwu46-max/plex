"""Personalized resource generation and teacher review API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.course_safety import SafetyViolation
from app.services.personalized_resource import PersonalizedResourceService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

personalized_resources_bp = Blueprint(
    'personalized_resources', __name__, url_prefix='/api/v1'
)


@personalized_resources_bp.route('/student/resource-generation/tasks', methods=['POST'])
@jwt_required()
@role_required('student')
def create_resource_task():
    try:
        return success_response(PersonalizedResourceService.create_task(
            int(get_jwt_identity()), request.get_json() or {}
        ), '生成任务已创建', status_code=201)
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)
    except ValueError as exc:
        code = 40011 if '课程范围' in str(exc) else 40010 if '不允许' in str(exc) else 40001
        payload = request.get_json(silent=True) or {}
        reason_code = (
            'invalid_resource_type'
            if 'resource_types' in payload
            else 'invalid_knowledge_key'
            if 'knowledge_key' in payload
            else 'invalid_request'
        )
        return error_response(str(exc), code, {'reason_code': reason_code}, 400)


@personalized_resources_bp.route('/student/resource-generation/tasks', methods=['GET'])
@jwt_required()
@role_required('student')
def list_resource_tasks():
    return success_response(PersonalizedResourceService.list_tasks(
        int(get_jwt_identity()),
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 20, type=int),
    ))


@personalized_resources_bp.route('/student/resource-generation/tasks/<task_id>', methods=['GET'])
@jwt_required()
@role_required('student')
def get_resource_task(task_id):
    try:
        return success_response(PersonalizedResourceService.get_task(int(get_jwt_identity()), task_id))
    except LookupError as exc:
        return error_response(str(exc), 40401, None, 404)


@personalized_resources_bp.route('/student/resource-generation/tasks/<task_id>/retry', methods=['POST'])
@jwt_required()
@role_required('student')
def retry_resource_task(task_id):
    try:
        return success_response(PersonalizedResourceService.retry(int(get_jwt_identity()), task_id), status_code=201)
    except LookupError as exc:
        return error_response(str(exc), 40401, None, 404)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@personalized_resources_bp.route('/student/personalized-resources', methods=['GET'])
@jwt_required()
@role_required('student')
def list_personalized_resources():
    return success_response(PersonalizedResourceService.list_student(
        int(get_jwt_identity()), request.args
    ))


@personalized_resources_bp.route('/teacher/personalized-resources/review', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_resource_review():
    return success_response(PersonalizedResourceService.list_review(
        request.args.get('review_status', 'pending_review')
    ))


@personalized_resources_bp.route('/teacher/personalized-resources/metrics', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def resource_review_metrics():
    return success_response(PersonalizedResourceService.review_metrics())


@personalized_resources_bp.route('/teacher/personalized-resources/<int:resource_id>/audit', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_resource_audit(resource_id):
    try:
        return success_response(PersonalizedResourceService.get_audit(resource_id))
    except LookupError as exc:
        return error_response(str(exc), 40401, None, 404)


@personalized_resources_bp.route('/teacher/personalized-resources/<int:resource_id>/audit/rerun', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def rerun_resource_audit(resource_id):
    try:
        return success_response(PersonalizedResourceService.rerun_audit(resource_id), '审核已重新执行')
    except LookupError as exc:
        return error_response(str(exc), 40401, None, 404)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@personalized_resources_bp.route('/teacher/personalized-resources/<int:resource_id>/review', methods=['PUT'])
@jwt_required()
@role_required('teacher', 'admin')
def review_resource(resource_id):
    try:
        payload = request.get_json() or {}
        return success_response(PersonalizedResourceService.review(
            resource_id,
            int(get_jwt_identity()),
            payload.get('review_status') or '',
            payload.get('reason') or '',
        ))
    except LookupError as exc:
        return error_response(str(exc), 40401, None, 404)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
