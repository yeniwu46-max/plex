"""班级变更审批服务。"""
from datetime import datetime

from app.models import Class, ClassChangeRequest, User, db
from app.services.class_service import ClassService
from app.utils.access import can_manage_classes, is_admin, teacher_owns_class


class ClassRequestService:
    @staticmethod
    def create_request(requester_id: int, action: str, payload: dict, class_id: int | None = None, reason: str | None = None):
        user = User.query.get(requester_id)
        if not user:
            raise ValueError('用户不存在')

        action = (action or '').strip().lower()
        if action not in ('create', 'update', 'delete'):
            raise ValueError('无效的申请类型')

        if is_admin(user) and can_manage_classes(user):
            raise ValueError('管理员请直接操作班级，无需提交审批')

        if action in ('update', 'delete'):
            if not class_id:
                raise ValueError('缺少 class_id')
            if not teacher_owns_class(user, class_id):
                raise PermissionError('只能为自己负责的班级提交申请')

        if action == 'create':
            required = ['name', 'teacher_id']
            for field in required:
                if not payload.get(field):
                    raise ValueError(f'缺少字段: {field}')
            if int(payload['teacher_id']) != user.id:
                raise PermissionError('教师只能为自己申请新建班级')

        pending = ClassChangeRequest.query.filter_by(
            requester_id=requester_id,
            action=action,
            class_id=class_id,
            status='pending',
        ).first()
        if pending:
            raise ValueError('已有相同类型的待审申请，请等待管理员处理')

        row = ClassChangeRequest(
            requester_id=requester_id,
            action=action,
            class_id=class_id,
            reason=reason,
            status='pending',
        )
        row.payload = payload
        db.session.add(row)
        db.session.commit()
        return row

    @staticmethod
    def list_requests(status: str | None = None, requester_id: int | None = None):
        query = ClassChangeRequest.query
        if status:
            query = query.filter_by(status=status)
        if requester_id:
            query = query.filter_by(requester_id=requester_id)
        rows = query.order_by(ClassChangeRequest.created_at.desc()).limit(100).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def review(request_id: int, reviewer_id: int, approve: bool, note: str | None = None):
        row = ClassChangeRequest.query.get(request_id)
        if not row:
            raise ValueError('申请不存在')
        if row.status != 'pending':
            raise ValueError('该申请已处理')

        reviewer = User.query.get(reviewer_id)
        if not reviewer or not is_admin(reviewer):
            raise PermissionError('仅管理员可审批')

        row.reviewer_id = reviewer_id
        row.review_note = note
        row.reviewed_at = datetime.utcnow()

        if not approve:
            row.status = 'rejected'
            db.session.commit()
            return row

        payload = row.payload
        if row.action == 'create':
            ClassService.create_class(
                name=payload['name'],
                description=payload.get('description'),
                grade_level=payload.get('grade_level'),
                teacher_id=int(payload['teacher_id']),
            )
        elif row.action == 'update':
            ClassService.update_class(row.class_id, **payload)
        elif row.action == 'delete':
            ClassService.delete_class(row.class_id)

        row.status = 'approved'
        db.session.commit()
        return row
