"""创建星球命名班级、分配学生、发布试炼并写入演示答题记录（不重置数据库）。"""
import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault('DATABASE_URL', 'sqlite:///instance/learning_system.db')

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import (
    Class,
    Role,
    Trial,
    TrialQuestion,
    User,
)
from app.services.question_generator import QuestionGenerator

TEACHER_USERNAME = 'teacher001'
PLANET_CLASS_NAME = '水星轨站·探索一班'
PLANET_CLASS_DESC = 'PLEX 水星轨站领航班级 · 近太阳轨道编制'
TRIAL_TITLE = '水星知识跃迁试炼'
STUDENT_USERNAMES = ['student001', 'student002', 'student003', 'student004', 'student005']


def _ensure_class(teacher: User) -> Class:
    target = Class.query.filter_by(teacher_id=teacher.id, name=PLANET_CLASS_NAME).first()
    if target:
        target.description = PLANET_CLASS_DESC
        return target

    legacy = Class.query.filter_by(teacher_id=teacher.id).order_by(Class.id.asc()).first()
    if legacy:
        legacy.name = PLANET_CLASS_NAME
        legacy.description = PLANET_CLASS_DESC
        return legacy

    target = Class(
        name=PLANET_CLASS_NAME,
        description=PLANET_CLASS_DESC,
        grade_level=1,
        teacher_id=teacher.id,
    )
    db.session.add(target)
    db.session.flush()
    return target


def _assign_students(target_class: Class, student_role: Role) -> list[User]:
    assigned: list[User] = []
    for username in STUDENT_USERNAMES:
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                email=f'{username}@example.com',
                password_hash=generate_password_hash('student123'),
                real_name=f'探索者-{username[-3:]}',
                role_id=student_role.id,
                class_id=target_class.id,
                level=1,
                total_points=100,
                status='active',
            )
            db.session.add(user)
            db.session.flush()
        else:
            user.class_id = target_class.id
            if not user.role_id:
                user.role_id = student_role.id
        assigned.append(user)
    return assigned


def _ensure_running_trial(target_class: Class, teacher: User) -> Trial:
    trial = (
        Trial.query.filter_by(class_id=target_class.id, title=TRIAL_TITLE)
        .order_by(Trial.id.desc())
        .first()
    )
    now = datetime.utcnow()
    if not trial:
        trial = Trial(
            class_id=target_class.id,
            teacher_id=teacher.id,
            title=TRIAL_TITLE,
            trial_type='solo',
            knowledge_key='dp',
            difficulty=72,
            duration_minutes=90,
            status='running',
            reward_points=40,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=8),
        )
        trial.set_knowledge_keys(['dp', 'graph', 'algo'])
        db.session.add(trial)
        db.session.flush()
    else:
        trial.title = TRIAL_TITLE

    if trial.status != 'running':
        trial.status = 'running'
        trial.starts_at = trial.starts_at or now - timedelta(hours=1)
        trial.ends_at = trial.ends_at or now + timedelta(hours=8)

    QuestionGenerator.ensure_for_trial(trial)
    return trial


def main() -> int:
    app = create_app('development')
    with app.app_context():
        db.create_all()
        from app.utils.db_migrate import ensure_trial_progress_columns

        ensure_trial_progress_columns()

        teacher = User.query.filter_by(username=TEACHER_USERNAME).first()
        if not teacher:
            print(f'未找到教师 {TEACHER_USERNAME}，请先运行 init_db.py', file=sys.stderr)
            return 1

        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            print('未找到 student 角色', file=sys.stderr)
            return 1

        target_class = _ensure_class(teacher)
        students = _assign_students(target_class, student_role)
        trial = _ensure_running_trial(target_class, teacher)

        # 不再写入演示答题记录；学生作答仅来自前端 POST /student/assignments/{id}/answer

        student_count = User.query.filter_by(class_id=target_class.id, role_id=student_role.id).count()
        target_class.student_count = student_count
        db.session.commit()

        q_count = TrialQuestion.query.filter_by(trial_id=trial.id).count()
        print(f'班级: {target_class.name} (id={target_class.id})')
        print(f'教师: {teacher.real_name} ({TEACHER_USERNAME})')
        print(f'学生数: {student_count}')
        print('已分配学生:', ', '.join(s.username for s in students))
        print(f'进行中试炼: {trial.title} (id={trial.id}, 题目 {q_count} 道)')
        print('答题记录需由学生在试炼关卡/探索舱/今日委托中提交后才会出现')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
