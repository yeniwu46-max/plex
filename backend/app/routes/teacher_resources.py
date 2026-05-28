"""教师知识库、作业模板"""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.data.knowledge_catalog import KNOWLEDGE_UNIVERSE
from app.services.teacher_template import TeacherTemplateService
from app.services.trial import TrialService
from app.models import User
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

teacher_resources_bp = Blueprint('teacher_resources', __name__, url_prefix='/api/v1/teacher')


def _role_name(user_id: int) -> str:
    user = User.query.get(user_id)
    return user.role.name if user and user.role else ''


@teacher_resources_bp.route('/knowledge-catalog', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_knowledge_catalog():
    return success_response({'domains': KNOWLEDGE_UNIVERSE})


@teacher_resources_bp.route('/templates', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def list_templates():
    try:
        teacher_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        return success_response(TeacherTemplateService.list_for_teacher(teacher_id, class_id))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_resources_bp.route('/templates', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def create_template():
    try:
        teacher_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        return success_response(TeacherTemplateService.create(teacher_id, payload), '模板已保存')
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_resources_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@jwt_required()
@role_required('teacher', 'admin')
def delete_template(template_id):
    try:
        teacher_id = int(get_jwt_identity())
        TeacherTemplateService.delete(teacher_id, template_id)
        return success_response(None, '模板已删除')
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_resources_bp.route('/templates/<int:template_id>/publish', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def publish_template(template_id):
    try:
        teacher_id = int(get_jwt_identity())
        payload = request.get_json() or {}
        class_id = payload.get('class_id', type=int)
        if not class_id:
            return error_response('class_id 不能为空', 40001, None, 400)
        notify = payload.get('notify_students', True)
        result = TeacherTemplateService.publish_template(
            teacher_id, _role_name(teacher_id), template_id, class_id, notify=bool(notify)
        )
        return success_response(result, '作业已发布')
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
