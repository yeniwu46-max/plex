"""Student profile API."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

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
