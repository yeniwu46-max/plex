"""Counterexample authoring, owned attempts, and safe published views."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.services.counterexample import CounterexampleService as Service
from app.services.counterexample_attempt import CounterexampleAttemptService as Attempts
from app.services.counterexample_generation import CounterexampleGenerationService as Generation
from app.services.counterexample_catalog import CounterexampleCatalogService as Catalog
from app.services.counterexample_contract import CounterexampleError, integer
from app.utils.decorators import role_required
from app.utils.response import success_response

counterexample_bp = Blueprint('counterexample', __name__, url_prefix='/api/v1')


def uid():
    return int(get_jwt_identity())


def query_integer(name, default=None):
    raw = request.args.get(name)
    if raw is None and default is not None:
        return default
    if not raw or not raw.isascii() or not raw.isdecimal() or len(raw) > 10:
        raise CounterexampleError(f'{name} 必须是正整数')
    return integer(int(raw), name, 1, 2**31-1)


@counterexample_bp.get('/teacher/counterexample-templates')
@jwt_required()
@role_required('teacher', 'admin')
def list_counterexample_templates():
    return success_response(Catalog.list(uid(), query_integer('class_id')))


@counterexample_bp.get('/teacher/counterexample-templates/<template_id>')
@jwt_required()
@role_required('teacher', 'admin')
def get_counterexample_template(template_id):
    return success_response(Catalog.get(uid(), query_integer('class_id'), template_id, request.args.get('content_hash')))


@counterexample_bp.post('/teacher/counterexample-generation-tasks')
@jwt_required()
@role_required('teacher', 'admin')
def create_generation_task():
    return success_response(Generation.create(uid(), request.get_json(silent=True)))


@counterexample_bp.get('/teacher/counterexample-generation-tasks')
@jwt_required()
@role_required('teacher', 'admin')
def list_generation_tasks():
    return success_response(Generation.list(uid(), query_integer('class_id'), query_integer('page', 1)))


@counterexample_bp.get('/teacher/counterexample-generation-tasks/<task_id>')
@jwt_required()
@role_required('teacher', 'admin')
def read_generation_task(task_id):
    return success_response(Generation.read(uid(), task_id))


@counterexample_bp.post('/teacher/counterexample-generation-tasks/<task_id>/cancel')
@jwt_required()
@role_required('teacher', 'admin')
def cancel_generation_task(task_id):
    return success_response(Generation.cancel(uid(), task_id))


@counterexample_bp.post('/teacher/counterexample-generation-tasks/<task_id>/retry')
@jwt_required()
@role_required('teacher', 'admin')
def retry_generation_task(task_id):
    return success_response(Generation.retry(uid(), task_id, request.get_json(silent=True)))


@counterexample_bp.get('/teacher/counterexample-challenges')
@jwt_required()
@role_required('teacher', 'admin')
def teacher_challenges():
    return success_response(Service.list_teacher(uid(), query_integer('class_id'), query_integer('page', 1)))


@counterexample_bp.get('/teacher/counterexample-specifications/<spec_id>')
@jwt_required()
@role_required('teacher', 'admin')
def teacher_specification(spec_id):
    return success_response(Service.get_spec(uid(), spec_id))


@counterexample_bp.get('/teacher/counterexample-challenges/<challenge_id>/versions')
@jwt_required()
@role_required('teacher', 'admin')
def teacher_versions(challenge_id):
    return success_response(Service.version_history(uid(), challenge_id, query_integer('page', 1)))


@counterexample_bp.get('/teacher/counterexample-challenges/<challenge_id>/versions/<int:revision>')
@jwt_required()
@role_required('teacher', 'admin')
def teacher_version(challenge_id, revision):
    return success_response(Service.get_teacher(uid(), challenge_id, revision))


@counterexample_bp.get('/teacher/counterexample-challenges/<challenge_id>/attempts')
@jwt_required()
@role_required('teacher', 'admin')
def teacher_attempts(challenge_id):
    return success_response(Attempts.list_teacher(uid(), challenge_id, query_integer('page', 1)))


@counterexample_bp.post('/teacher/counterexample-specifications')
@jwt_required()
@role_required('teacher', 'admin')
def create_specification():
    return success_response(Service.create_spec(uid(), request.get_json(silent=True)))


@counterexample_bp.post('/teacher/counterexample-challenges')
@jwt_required()
@role_required('teacher', 'admin')
def create_challenge():
    return success_response(Service.create(uid(), request.get_json(silent=True)))


@counterexample_bp.get('/teacher/counterexample-challenges/<challenge_id>')
@jwt_required()
@role_required('teacher', 'admin')
def get_challenge(challenge_id):
    return success_response(Service.get_teacher(uid(), challenge_id))


@counterexample_bp.post('/teacher/counterexample-challenges/<challenge_id>/versions')
@jwt_required()
@role_required('teacher', 'admin')
def revise_challenge(challenge_id):
    return success_response(Service.revise(uid(), challenge_id, request.get_json(silent=True)))


@counterexample_bp.post('/teacher/counterexample-challenges/<challenge_id>/validate')
@jwt_required()
@role_required('teacher', 'admin')
def validate_challenge(challenge_id):
    return success_response(Service.validate(uid(), challenge_id, request.get_json(silent=True)))


@counterexample_bp.post('/teacher/counterexample-challenges/<challenge_id>/review')
@jwt_required()
@role_required('teacher', 'admin')
def review_challenge(challenge_id):
    return success_response(Service.review(uid(), challenge_id, request.get_json(silent=True)))


@counterexample_bp.get('/student/counterexample-challenges')
@jwt_required()
@role_required('student')
def student_challenges():
    return success_response(Service.list_student(uid()))


@counterexample_bp.get('/student/counterexample-challenges/<challenge_id>')
@jwt_required()
@role_required('student')
def student_challenge(challenge_id):
    return success_response(Service.get_student(uid(), challenge_id))


@counterexample_bp.post('/student/counterexample-challenges/<challenge_id>/attempts')
@jwt_required()
@role_required('student')
def submit_counterexample(challenge_id):
    return success_response(Attempts.submit(uid(), challenge_id, request.get_json(silent=True)))


@counterexample_bp.get('/student/counterexample-challenges/<challenge_id>/attempts')
@jwt_required()
@role_required('student')
def list_counterexample_attempts(challenge_id):
    return success_response(Attempts.list_owned(uid(), challenge_id))


@counterexample_bp.get('/student/counterexample-attempts/<request_id>')
@jwt_required()
@role_required('student')
def read_counterexample_attempt(request_id):
    return success_response(Attempts.read(uid(), request_id))


@counterexample_bp.get('/teacher/counterexample-attempts/<request_id>')
@jwt_required()
@role_required('teacher', 'admin')
def teacher_counterexample_attempt(request_id):
    return success_response(Attempts.teacher_read(uid(), request_id))


@counterexample_bp.post('/teacher/counterexample-attempts/<request_id>/review')
@jwt_required()
@role_required('teacher', 'admin')
def review_counterexample_explanation(request_id):
    return success_response(Attempts.review(uid(), request_id, request.get_json(silent=True)))
