"""Teacher workspace routes."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User, db
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.assignment import AssignmentService
from app.services.evaluation import EvaluationService
from app.services.mistake import MistakeService
from app.services.teacher import TeacherService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response

teacher_bp = Blueprint('teacher', __name__, url_prefix='/api/v1/teacher')


def _role_name(user_id):
    user = db.session.get(User, int(user_id))
    return user.role.name if user and user.role else None


def _guard_teacher_student(current_user_id, student_id):
    """确认当前教师有权访问该学生，并返回学生对象。"""
    from app.services.trial import TrialService

    student = db.session.get(User, int(student_id))
    if not student or not student.class_id:
        raise ValueError('学生不存在或未分班')
    if not student.role or student.role.name != 'student':
        raise ValueError('目标用户不是学生')
    TrialService._get_teacher_class(student.class_id, current_user_id, _role_name(current_user_id))
    return student


@teacher_bp.route('/overview', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_teacher_overview():
    """Return the teacher dashboard aggregate for one class."""
    try:
        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        period = request.args.get('period', 'week')
        return success_response(TeacherService.get_overview(current_user_id, class_id, period))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/class-stats', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_teacher_class_stats():
    try:
        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        return success_response(TeacherService.get_class_stats(current_user_id, class_id))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/online-students', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_online_students():
    """班级实时在线学员名单（基于心跳 presence）。"""
    try:
        from app.services.presence import PresenceService
        from app.services.trial import TrialService

        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        if not class_id:
            overview = TeacherService.get_overview(current_user_id, None, 'week')
            class_id = (overview.get('selected_class') or {}).get('id')
        if class_id:
            TrialService._get_teacher_class(class_id, current_user_id, _role_name(current_user_id))
        return success_response(PresenceService.class_online_students(class_id))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/profile', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_teacher_profile():
    """教师个人信息小页：头像、姓名、性别、管理班级、联系方式、在线状态。"""
    try:
        current_user_id = int(get_jwt_identity())
        user = db.session.get(User, current_user_id)
        if not user:
            return error_response('用户不存在', 40401, None, 404)
        classes = TeacherService.list_classes(current_user_id) if hasattr(TeacherService, 'list_classes') else []
        if not classes:
            from app.models import Class
            if user.role and user.role.name == 'admin':
                class_rows = Class.query.order_by(Class.id.asc()).all()
            else:
                class_rows = Class.query.filter_by(teacher_id=current_user_id).order_by(Class.id.asc()).all()
            classes = [
                {
                    'id': row.id,
                    'name': row.name,
                    'student_count': row.student_count or 0,
                    'join_code': row.join_code,
                }
                for row in class_rows
            ]
        return success_response({
            'id': user.id,
            'username': user.username,
            'real_name': user.real_name,
            'gender': user.gender or 'other',
            'email': user.email,
            'phone': user.phone,
            'avatar_url': user.avatar_url,
            'bio': user.bio,
            'status': user.status or 'active',
            'online': True,
            'classes': classes,
        })
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/classes/<int:class_id>/trial-answers', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_class_trial_answers(class_id):
    """班级维度：查看所有试炼的学生作答明细（与学生端提交同步）。"""
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(
            AssignmentService.get_class_answer_board(current_user_id, class_id, _role_name(current_user_id))
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/students/<int:student_id>/trial-answers', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_student_trial_answers(student_id):
    """学生维度：查看某 Explorer 在各试炼中的逐题作答。"""
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(
            AssignmentService.get_student_answer_board(current_user_id, student_id, _role_name(current_user_id))
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/students/<int:student_id>/mistakes', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_student_mistakes(student_id):
    try:
        current_user_id = int(get_jwt_identity())
        return success_response(
            MistakeService.list_for_teacher_student(
                current_user_id,
                student_id,
                _role_name(current_user_id),
            )
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/students/<int:student_id>/learning-report', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_student_learning_report(student_id):
    try:
        current_user_id = int(get_jwt_identity())
        period = request.args.get('period', '7d')
        return success_response(
            EvaluationService.get_teacher_student_report(
                current_user_id,
                student_id,
                _role_name(current_user_id),
                period,
            )
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/students/<int:student_id>/learning-adaptations', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_student_learning_adaptations(student_id):
    try:
        current_user_id = int(get_jwt_identity())
        MistakeService.list_for_teacher_student(current_user_id, student_id, _role_name(current_user_id))
        from app.services.learning_adaptation import LearningAdaptationService
        return success_response(LearningAdaptationService.teacher_summary(student_id))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)


@teacher_bp.route('/students/<int:student_id>/learning-effect', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_student_learning_effect(student_id):
    try:
        current_user_id = int(get_jwt_identity())
        task_id = request.args.get('task_id')
        return success_response(
            EvaluationService.get_teacher_learning_effect(
                current_user_id,
                student_id,
                _role_name(current_user_id),
                task_id,
            )
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/class-evaluation', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_class_evaluation():
    try:
        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        period = request.args.get('period', '7d')
        return success_response(
            EvaluationService.get_class_evaluation(current_user_id, class_id, period)
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/class-diagnosis', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def get_class_diagnosis():
    """班级一键学情诊断：聚合班级错题与知识图谱薄弱点，调用教师助理智能体。"""
    try:
        from app.services.trial import TrialService

        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        if not class_id:
            return error_response('class_id 必填', 40001, None, 400)
        cls = TrialService._get_teacher_class(class_id, current_user_id, _role_name(current_user_id))
        result = AgentOrchestrator.class_diagnosis(cls.id)
        if isinstance(result, dict):
            result.setdefault('class_id', cls.id)
        return success_response(result)
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/students/<int:student_id>/diagnose', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def diagnose_student(student_id):
    """教师视角：基于该学生已留存的错题证据运行一次学情诊断。"""
    try:
        current_user_id = int(get_jwt_identity())
        _guard_teacher_student(current_user_id, student_id)
        return success_response(AgentOrchestrator.diagnose_learning_overview(student_id))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/students/<int:student_id>/plan-path', methods=['POST'])
@jwt_required()
@role_required('teacher', 'admin')
def plan_student_path(student_id):
    """教师视角：为指定学生规划个性化学习路径。"""
    try:
        current_user_id = int(get_jwt_identity())
        _guard_teacher_student(current_user_id, student_id)
        body = request.get_json(silent=True) or {}
        return success_response(AgentOrchestrator.plan_learning_path(student_id, body))
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@teacher_bp.route('/class-export', methods=['GET'])
@jwt_required()
@role_required('teacher', 'admin')
def export_class_evaluation():
    try:
        from flask import Response

        current_user_id = int(get_jwt_identity())
        class_id = request.args.get('class_id', type=int)
        if not class_id:
            return error_response('class_id 必填', 40001, None, 400)
        csv_text = EvaluationService.export_class_csv(
            current_user_id,
            class_id,
            _role_name(current_user_id),
        )
        return Response(
            csv_text,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename=class_{class_id}_evaluation.csv'},
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
