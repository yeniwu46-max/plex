from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models import db
from app.models.student_practice import MockExam
from app.services.student_practice import StudentPractice, MockExams
from app.services.tutor_context import TutorContextError
from app.utils.decorators import role_required
from app.utils.response import success_response, error_response

student_practice_bp = Blueprint('student_practice', __name__, url_prefix='/api/v1/student')


@student_practice_bp.errorhandler(TutorContextError)
def context_error(exc):
    db.session.rollback()
    return error_response(str(exc), exc.status * 100 + 1, None, exc.status)


@student_practice_bp.errorhandler(ValueError)
def value_error(exc):
    db.session.rollback()
    return error_response(str(exc), 40001, None, 400)


def uid():
    return int(get_jwt_identity())


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError('请求体必须是 JSON 对象')
    return value


@student_practice_bp.route('/question-favorites/<path:ref>', methods=['PUT', 'DELETE'])
@jwt_required()
@role_required('student')
def favorite(ref):
    return success_response(StudentPractice.favorite(uid(), ref, request.method == 'PUT'))


@student_practice_bp.post('/practice-submissions/<path:ref>')
@jwt_required()
@role_required('student')
def submit(ref):
    return success_response(StudentPractice.submit(uid(), ref, body()))


@student_practice_bp.get('/practice-history')
@jwt_required()
@role_required('student')
def history():
    return success_response(StudentPractice.history(uid(), request.args))


@student_practice_bp.route('/mock-exams', methods=['GET', 'POST'])
@jwt_required()
@role_required('student')
def exams():
    if request.method == 'POST':
        return success_response(MockExams.create(uid(), body()))
    rows = MockExam.query.filter_by(user_id=uid()).order_by(MockExam.started_at.desc()).limit(20).all()
    return success_response({'items': [MockExams.view(uid(), row.id) for row in rows]})


@student_practice_bp.get('/mock-exams/<eid>')
@jwt_required()
@role_required('student')
def exam(eid):
    return success_response(MockExams.view(uid(), eid))


@student_practice_bp.patch('/mock-exams/<eid>/answers')
@jwt_required()
@role_required('student')
def answers(eid):
    return success_response(MockExams.save(uid(), eid, body()))


@student_practice_bp.post('/mock-exams/<eid>/submit')
@jwt_required()
@role_required('student')
def finish(eid):
    MockExams.lock(uid(), eid)
    return success_response(MockExams.view(uid(), eid))


@student_practice_bp.get('/resource-trash')
@jwt_required()
@role_required('student')
def trash_list():
    from app.services.resource_trash import ResourceTrash
    return success_response(ResourceTrash.list(uid(), request.args))


@student_practice_bp.delete('/personalized-resources/<int:resource_id>')
@jwt_required()
@role_required('student')
def trash_resource(resource_id):
    from app.services.resource_trash import ResourceTrash
    return success_response(ResourceTrash.move(uid(), resource_id=resource_id))


@student_practice_bp.delete('/resource-packages/<task_id>')
@jwt_required()
@role_required('student')
def trash_package(task_id):
    from app.services.resource_trash import ResourceTrash
    return success_response(ResourceTrash.move(uid(), task_id=task_id))


@student_practice_bp.post('/resource-trash/restore')
@jwt_required()
@role_required('student')
def restore_resource():
    from app.services.resource_trash import ResourceTrash
    value = body()
    if bool(value.get('resource_id')) == bool(value.get('batch_id')):
        raise ValueError('请选择资源或删除批次')
    return success_response(ResourceTrash.restore(uid(), resource_id=value.get('resource_id'), batch_id=value.get('batch_id')))


@student_practice_bp.get('/practice-history/<attempt_id>')
@jwt_required()
@role_required('student')
def history_item(attempt_id):
    from app.models.student_practice import PracticeAttempt
    row = db.session.get(PracticeAttempt, attempt_id)
    if not row or row.user_id != uid():
        raise TutorContextError('作答记录不存在', 404)
    return success_response(row.to_dict())


@student_practice_bp.get('/personalized-resources/<int:resource_id>')
@jwt_required()
@role_required('student')
def resource_detail(resource_id):
    from app.models.personalized_resource import PersonalizedLearningResource
    from app.services.resource_course_evidence import ResourceCourseEvidence
    row = db.session.get(PersonalizedLearningResource, resource_id)
    if not row or row.user_id != uid() or row.deleted_at or row.review_status == 'rejected' or not ResourceCourseEvidence.resource_current(row):
        raise TutorContextError('资源已删除或不可用', 404)
    return success_response(row.to_dict())
