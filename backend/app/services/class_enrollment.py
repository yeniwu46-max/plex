"""学生入班申请服务。"""
from app.models import Class, ClassEnrollmentRequest, User, db
from app.services.class_service import ClassService
from app.utils.access import can_manage_classes, is_admin, teacher_owns_class
from app.utils.time import utc_now


class ClassEnrollmentService:
    @staticmethod
    def _require_student(user: User) -> None:
        if not user.role or user.role.name != 'student':
            raise PermissionError('仅学生可提交入班申请')

    @staticmethod
    def lookup_class(join_code: str) -> dict:
        class_obj = ClassService.get_class_by_join_code(join_code)
        if not class_obj:
            raise ValueError('班级编号无效，请核对后重试')
        return {
            'class_id': class_obj.id,
            'class_name': class_obj.name,
            'teacher_name': class_obj.teacher.real_name if class_obj.teacher else None,
            'student_count': class_obj.student_count,
            'join_code': class_obj.join_code,
        }

    @staticmethod
    def apply(student_id: int, join_code: str, message: str | None = None):
        student = db.session.get(User, student_id)
        if not student:
            raise ValueError('用户不存在')
        ClassEnrollmentService._require_student(student)

        class_obj = ClassService.get_class_by_join_code(join_code)
        if not class_obj:
            raise ValueError('班级编号无效，请核对后重试')

        if student.class_id == class_obj.id:
            raise ValueError('你已在该班级中')

        pending = ClassEnrollmentRequest.query.filter_by(
            student_id=student_id,
            class_id=class_obj.id,
            status='pending',
        ).first()
        if pending:
            raise ValueError('你已提交过该班级的入班申请，请等待教师审核')

        row = ClassEnrollmentRequest(
            student_id=student_id,
            class_id=class_obj.id,
            message=(message or '').strip() or None,
            status='pending',
        )
        db.session.add(row)
        db.session.commit()
        return row

    @staticmethod
    def list_for_student(student_id: int, status: str | None = None):
        query = ClassEnrollmentRequest.query.filter_by(student_id=student_id)
        if status:
            query = query.filter_by(status=status)
        rows = query.order_by(ClassEnrollmentRequest.created_at.desc()).limit(50).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def list_for_teacher(teacher_id: int, status: str | None = None, class_id: int | None = None):
        class_ids = [c.id for c in Class.query.filter_by(teacher_id=teacher_id).all()]
        if not class_ids:
            return []

        query = ClassEnrollmentRequest.query.filter(ClassEnrollmentRequest.class_id.in_(class_ids))
        if class_id:
            if class_id not in class_ids:
                raise PermissionError('无权查看该班级的入班申请')
            query = query.filter_by(class_id=class_id)
        if status:
            query = query.filter_by(status=status)
        rows = query.order_by(ClassEnrollmentRequest.created_at.desc()).limit(100).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def list_for_admin(status: str | None = None, class_id: int | None = None):
        query = ClassEnrollmentRequest.query
        if class_id:
            query = query.filter_by(class_id=class_id)
        if status:
            query = query.filter_by(status=status)
        rows = query.order_by(ClassEnrollmentRequest.created_at.desc()).limit(100).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def review(request_id: int, reviewer_id: int, approve: bool, note: str | None = None):
        row = db.session.get(ClassEnrollmentRequest, request_id)
        if not row:
            raise ValueError('申请不存在')
        if row.status != 'pending':
            raise ValueError('该申请已处理')

        reviewer = db.session.get(User, reviewer_id)
        if not reviewer:
            raise ValueError('审核人不存在')

        if not is_admin(reviewer) and not teacher_owns_class(reviewer, row.class_id):
            raise PermissionError('仅该班负责教师可审核入班申请')

        row.reviewer_id = reviewer_id
        row.review_note = (note or '').strip() or None
        row.reviewed_at = utc_now()

        if not approve:
            row.status = 'rejected'
            db.session.commit()
            return row

        student = db.session.get(User, row.student_id)
        if not student:
            raise ValueError('学生不存在')

        ClassService.add_student_to_class(row.class_id, row.student_id)
        row.status = 'approved'
        db.session.commit()
        return row
