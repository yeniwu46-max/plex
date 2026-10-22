"""Authenticated read models and acknowledgement of server-issued help receipts."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models import db, User
from app.services.learner_state import LearnerStateService
from app.utils.access import teacher_owns_class
from app.utils.decorators import role_required
from app.utils.response import success_response, error_response

learner_state_bp = Blueprint('learner_state', __name__, url_prefix='/api/v1')


@learner_state_bp.get('/teacher/classes/<int:class_id>/learning-observations')
@jwt_required()
@role_required('teacher')
def class_observations(class_id):
    from app.services.pilot_observability import snapshot
    from app.services.tutor_context import TutorContextError
    try:
        raw = request.args.get('days', '14')
        if raw not in ('7', '14', '30'):
            raise TutorContextError('统计范围仅支持最近 7、14 或 30 天')
        return success_response(snapshot(int(get_jwt_identity()), class_id, int(raw)))
    except TutorContextError as exc:
        return error_response(str(exc), exc.status * 100 + 1, None, exc.status)


def _evidence_page(student_id):
    from app.services.learning_evidence import page, MAX_VERSION
    from app.services.tutor_context import TutorContextError
    try:
        if any(len(request.args.getlist(key)) > 1 for key in ('limit','cursor','snapshot_version')):
            raise TutorContextError('翻页参数不能重复')
        raw_limit = request.args.get('limit', '20')
        raw_version = request.args.get('snapshot_version')
        if not raw_limit.isascii() or not raw_limit.isdecimal() or len(raw_limit) > 2:
            raise TutorContextError('每页条数须为 1–50 的整数')
        if raw_version is not None and (not raw_version.isascii() or not raw_version.isdecimal() or len(raw_version) > 10):
            raise TutorContextError('学习状态版本无效')
        version = int(raw_version) if raw_version is not None else None
        if version is not None and version > MAX_VERSION:
            raise TutorContextError('学习状态版本无效')
        response = success_response(page(int(get_jwt_identity()), student_id, cursor=request.args.get('cursor'),
                                         limit=int(raw_limit), snapshot_version=version))
        response[0].headers['Cache-Control'] = 'no-store'
        return response
    except TutorContextError as exc:
        return error_response(str(exc), exc.status * 100 + 1, None, exc.status)


@learner_state_bp.get('/student/learning-evidence')
@jwt_required()
@role_required('student')
def own_evidence():
    return _evidence_page(int(get_jwt_identity()))


@learner_state_bp.get('/teacher/students/<int:student_id>/learning-evidence')
@jwt_required()
@role_required('teacher')
def teacher_evidence(student_id):
    return _evidence_page(student_id)


@learner_state_bp.get('/student/learner-state')
@jwt_required()
@role_required('student')
def get_state():
    return success_response(LearnerStateService.snapshot(int(get_jwt_identity())))


@learner_state_bp.post('/student/tutor-responses/<receipt_id>/displayed')
@jwt_required()
@role_required('student')
def acknowledge_hint(receipt_id):
    try:
        return success_response(LearnerStateService.acknowledge_hint(int(get_jwt_identity()), receipt_id))
    except LookupError:
        return error_response('提示不存在', 40401, None, 404)


@learner_state_bp.get('/teacher/students/<int:student_id>/learner-state')
@jwt_required()
@role_required('teacher')
def teacher_state(student_id):
    actor = db.session.get(User, int(get_jwt_identity()))
    student = db.session.get(User, student_id)
    if not student or not student.role or student.role.name != 'student' or not teacher_owns_class(actor, student.class_id):
        return error_response('无权查看该学生的学习状态', 40301, None, 403)
    return success_response(LearnerStateService.snapshot(student_id))


@learner_state_bp.post('/teacher/students/<int:student_id>/misconceptions/<int:misconception_id>/review')
@jwt_required()
@role_required('teacher')
def review_misconception(student_id, misconception_id):
    from app.services.misconception_review import MisconceptionReviewService, ReviewConflict
    try:
        result = MisconceptionReviewService.review(int(get_jwt_identity()), student_id,
            misconception_id, request.get_json(silent=True))
        return success_response(result)
    except PermissionError as exc:
        db.session.rollback()
        return error_response(str(exc), 40301, None, 403)
    except LookupError as exc:
        db.session.rollback()
        return error_response(str(exc), 40401, None, 404)
    except ReviewConflict as exc:
        db.session.rollback()
        return error_response(str(exc), 40901, None, 409)
    except ValueError as exc:
        db.session.rollback()
        return error_response(str(exc), 40001, None, 400)
