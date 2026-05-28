"""教师作业模板"""
from app.models import Class, TeacherTrialTemplate, Trial, User, db
from app.services.trial import TrialService


class TeacherTemplateService:
    @staticmethod
    def list_for_teacher(teacher_id: int, class_id: int | None = None):
        query = TeacherTrialTemplate.query.filter_by(teacher_id=teacher_id)
        if class_id is not None:
            query = query.filter(
                (TeacherTrialTemplate.class_id == class_id) | (TeacherTrialTemplate.class_id.is_(None))
            )
        rows = query.order_by(TeacherTrialTemplate.updated_at.desc()).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def create(teacher_id: int, payload: dict):
        keys = payload.get('knowledge_keys') or []
        if not keys:
            raise ValueError('请至少选择一个知识点')
        title = (payload.get('title') or '未命名模板').strip()[:120]
        row = TeacherTrialTemplate(
            teacher_id=teacher_id,
            class_id=payload.get('class_id'),
            title=title,
            trial_type=payload.get('trial_type') or 'solo',
            difficulty=int(payload.get('difficulty') or 60),
            duration_minutes=int(payload.get('duration_minutes') or 60),
            reward_points=int(payload.get('reward_points') or 35),
        )
        row.set_knowledge_keys(keys)
        db.session.add(row)
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def delete(teacher_id: int, template_id: int):
        row = TeacherTrialTemplate.query.get(template_id)
        if not row:
            raise ValueError('模板不存在')
        if row.teacher_id != teacher_id:
            raise PermissionError('无权删除该模板')
        db.session.delete(row)
        db.session.commit()

    @staticmethod
    def publish_template(teacher_id: int, role_name: str, template_id: int, class_id: int, notify: bool = True):
        row = TeacherTrialTemplate.query.get(template_id)
        if not row:
            raise ValueError('模板不存在')
        if row.teacher_id != teacher_id:
            raise PermissionError('无权使用该模板')
        keys = row.knowledge_keys()
        if not keys:
            raise ValueError('模板未包含知识点')

        payload = {
            'class_id': class_id,
            'title': row.title,
            'trial_type': row.trial_type,
            'knowledge_keys': keys,
            'knowledge_key': keys[0],
            'difficulty': row.difficulty,
            'duration_minutes': row.duration_minutes,
            'reward_points': row.reward_points,
            'publish_mode': 'now',
            'notify_students': bool(notify),
        }
        trial_dict = TrialService.create_trial(teacher_id, role_name, payload)
        from app.models import Role

        student_count = 0
        student_role = Role.query.filter_by(name='student').first()
        if student_role:
            student_count = User.query.filter_by(class_id=class_id, role_id=student_role.id).count()

        return {
            'trial': trial_dict,
            'notify_students': bool(notify),
            'student_count': student_count,
            'notifications_sent': trial_dict.get('notifications_sent', 0),
        }
