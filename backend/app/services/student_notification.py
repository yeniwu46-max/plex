"""学生站内通知"""
from app.models import Role, StudentNotification, User, db


class StudentNotificationService:
    @staticmethod
    def _students_in_class(class_id: int) -> list[User]:
        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            return []
        return User.query.filter_by(class_id=class_id, role_id=student_role.id).all()

    @staticmethod
    def notify_class_teacher_task(class_id: int, trial_id: int, trial_title: str, teacher_name: str = '老师'):
        if not class_id:
            return 0
        students = StudentNotificationService._students_in_class(class_id)
        if not students:
            return 0
        title = '老师发布了新的任务'
        body = f'{teacher_name} 发布了「{trial_title}」，快去今日委托或探索舱完成。'
        count = 0
        for student in students:
            exists = (
                StudentNotification.query.filter_by(
                    user_id=student.id,
                    kind='teacher_task_published',
                    trial_id=trial_id,
                ).first()
            )
            if exists:
                continue
            row = StudentNotification(
                user_id=student.id,
                kind='teacher_task_published',
                title=title,
                body=body,
                trial_id=trial_id,
                is_read=False,
            )
            db.session.add(row)
            count += 1
        if count:
            db.session.commit()
        return count

    @staticmethod
    def list_for_user(user_id: int, unread_only: bool = False, limit: int = 30):
        query = StudentNotification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        rows = query.order_by(StudentNotification.created_at.desc()).limit(limit).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def mark_read(user_id: int, notification_id: int):
        row = StudentNotification.query.filter_by(id=notification_id, user_id=user_id).first()
        if not row:
            raise ValueError('通知不存在')
        row.is_read = True
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def mark_all_read(user_id: int):
        StudentNotification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
