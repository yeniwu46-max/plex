"""Student profile API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.course_safety import SafetyViolation
from app.services.student_profile import StudentProfileService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

student_profile_bp = Blueprint('student_profile', __name__, url_prefix='/api/v1/student/profile')


@student_profile_bp.route('', methods=['GET'])
@jwt_required()
@role_required('student')
def get_profile():
    user_id = int(get_jwt_identity())
    return success_response(StudentProfileService.get_or_create(user_id).to_dict())


@student_profile_bp.route('/diagnostic', methods=['GET', 'POST'])
@jwt_required()
@role_required('student')
def diagnostic():
    user_id = int(get_jwt_identity())
    if request.method == 'GET':
        return success_response({'questions': StudentProfileService.diagnostic_questions(), 'diagnostic': StudentProfileService.diagnostic_status(user_id)})
    try:
        payload = request.get_json() or {}
        return success_response(StudentProfileService.submit_diagnostic(user_id, payload.get('answers'), bool(payload.get('skip'))))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@student_profile_bp.route('/adaptations', methods=['GET'])
@jwt_required()
@role_required('student')
def adaptations():
    from app.services.learning_adaptation import LearningAdaptationService
    return success_response({'items': LearningAdaptationService.active_for_student(int(get_jwt_identity()))})


@student_profile_bp.route('/chat', methods=['POST'])
@jwt_required()
@role_required('student')
def chat_profile():
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(StudentProfileService.chat(
            user_id,
            payload.get('message', ''),
            bool(payload.get('confirm_changes')),
        ))
    except SafetyViolation as exc:
        return error_response(str(exc), 40012, {'reason_code': exc.reason_code}, 400)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@student_profile_bp.route('', methods=['PUT'])
@jwt_required()
@role_required('student')
def update_profile():
    try:
        user_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(StudentProfileService.apply_changes(
            user_id,
            payload.get('changes') or {},
            payload.get('reason') or 'student_correction',
        ))
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)


@student_profile_bp.route('/history', methods=['GET'])
@jwt_required()
@role_required('student')
def profile_history():
    user_id = int(get_jwt_identity())
    return success_response(StudentProfileService.history(
        user_id,
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 20, type=int),
    ))


@student_profile_bp.route('/suggestions', methods=['GET'])
@jwt_required()
@role_required('student')
def profile_suggestions():
    return success_response(StudentProfileService.suggestions(
        int(get_jwt_identity()),
        request.args.get('status', 'pending'),
    ))


@student_profile_bp.route('/suggestions/<int:suggestion_id>', methods=['PUT'])
@jwt_required()
@role_required('student')
def resolve_profile_suggestion(suggestion_id):
    try:
        payload = request.get_json() or {}
        return success_response(StudentProfileService.resolve_suggestion(
            int(get_jwt_identity()),
            suggestion_id,
            payload.get('action') or '',
        ))
    except LookupError as exc:
        return error_response(str(exc), 40401, None, 404)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
