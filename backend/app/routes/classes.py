"""班级路由"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.class_service import ClassService
from app.utils.response import success_response, error_response
from app.utils.decorators import permission_required

classes_bp = Blueprint('classes', __name__, url_prefix='/api/v1/classes')


@classes_bp.route('', methods=['POST'])
@jwt_required()
@permission_required('manage_classes')
def create_class():
    """创建班级 - 需要 manage_classes 权限"""
    try:
        data = request.get_json()

        required_fields = ['name', 'teacher_id']
        for field in required_fields:
            if not data.get(field):
                return error_response(f'缺少必需字段: {field}', 40001)

        class_obj = ClassService.create_class(
            name=data['name'],
            description=data.get('description'),
            grade_level=data.get('grade_level'),
            teacher_id=data['teacher_id']
        )

        return success_response(class_obj.to_dict(), '班级创建成功', 0, 201)

    except Exception as e:
        return error_response(str(e), 40001)


@classes_bp.route('', methods=['GET'])
@jwt_required()
def get_classes():
    """获取班级列表 - 所有认证用户可访问"""
    try:
        teacher_id = request.args.get('teacher_id', type=int)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        result = ClassService.get_classes(
            teacher_id=teacher_id,
            page=page,
            limit=limit
        )

        return success_response(result)

    except Exception as e:
        return error_response(str(e), 50001)


@classes_bp.route('/<int:class_id>', methods=['GET'])
@jwt_required()
def get_class(class_id):
    """获取班级详情 - 所有认证用户可访问"""
    try:
        class_obj = ClassService.get_class(class_id)
        return success_response(class_obj.to_dict())

    except Exception as e:
        return error_response(str(e), 40401)


@classes_bp.route('/<int:class_id>', methods=['PUT'])
@jwt_required()
@permission_required('manage_classes')
def update_class(class_id):
    """更新班级 - 需要 manage_classes 权限"""
    try:
        data = request.get_json()
        class_obj = ClassService.update_class(class_id, **data)

        return success_response(class_obj.to_dict(), '班级更新成功')

    except Exception as e:
        return error_response(str(e), 50001)


@classes_bp.route('/<int:class_id>', methods=['DELETE'])
@jwt_required()
@permission_required('manage_classes')
def delete_class(class_id):
    """删除班级 - 需要 manage_classes 权限"""
    try:
        ClassService.delete_class(class_id)
        return success_response(None, '班级已删除')

    except Exception as e:
        return error_response(str(e), 50001)


@classes_bp.route('/<int:class_id>/students', methods=['POST'])
@jwt_required()
@permission_required('manage_classes')
def add_student(class_id):
    """添加学生到班级 - 需要 manage_classes 权限"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return error_response('缺少user_id', 40001)

        ClassService.add_student_to_class(class_id, user_id)

        return success_response(None, '学生已添加到班级', 0, 201)

    except Exception as e:
        return error_response(str(e), 50001)


@classes_bp.route('/<int:class_id>/students/<int:user_id>', methods=['DELETE'])
@jwt_required()
@permission_required('manage_classes')
def remove_student(class_id, user_id):
    """从班级移除学生 - 需要 manage_classes 权限"""
    try:
        ClassService.remove_student_from_class(class_id, user_id)
        return success_response(None, '学生已从班级移除')

    except Exception as e:
        return error_response(str(e), 50001)


@classes_bp.route('/<int:class_id>/ranking', methods=['GET'])
@jwt_required()
def get_class_ranking(class_id):
    """获取班级排名 - 所有认证用户可访问"""
    try:
        week = request.args.get('week')
        result = ClassService.get_class_ranking(class_id, week)
        return success_response(result)

    except Exception as e:
        return error_response(str(e), 50001)
