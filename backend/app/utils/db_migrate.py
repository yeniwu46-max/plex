"""轻量 SQLite 列迁移（无 Alembic 时补齐新字段）。"""
from sqlalchemy import inspect, text

from app.models import db


def ensure_trial_progress_columns() -> None:
    inspector = inspect(db.engine)
    if 'trial_question_progress' not in inspector.get_table_names():
        return

    existing = {col['name'] for col in inspector.get_columns('trial_question_progress')}
    additions = {
        'started_at': 'DATETIME',
        'time_spent_sec': 'INTEGER',
        'selected_label': 'VARCHAR(8)',
        'agent_trace_json': 'TEXT',
    }
    for name, col_type in additions.items():
        if name in existing:
            continue
        db.session.execute(text(f'ALTER TABLE trial_question_progress ADD COLUMN {name} {col_type}'))
    db.session.commit()


def ensure_class_enrollment_schema() -> None:
    """补齐班级编号与入班申请表（本地 db.create_all 后的增量）。"""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if 'classes' in tables:
        class_columns = {col['name'] for col in inspector.get_columns('classes')}
        if 'join_code' not in class_columns:
            db.session.execute(text('ALTER TABLE classes ADD COLUMN join_code VARCHAR(8)'))
            db.session.commit()

    if 'class_enrollment_requests' not in tables:
        db.create_all()
        db.session.commit()

    from app.services.class_service import ClassService

    ClassService.ensure_join_codes()


def ensure_trial_comments_schema() -> None:
    """补齐试炼题目评论表（本地 db.create_all 后的增量）。"""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if 'trial_comments' not in tables or 'trial_comment_likes' not in tables:
        db.create_all()
        db.session.commit()


def ensure_practice_question_schema() -> None:
    """启动时审计并迁移 coding 题 stem 中嵌入的测试样例到 coding_meta。"""
    try:
        from scripts.audit_practice_questions import audit_and_migrate

        audit_and_migrate(dry_run=False)
    except Exception:
        pass


def ensure_resource_audit_schema() -> None:
    """补齐资源生成任务的 audit_report 列。"""
    inspector = inspect(db.engine)
    if 'resource_generation_tasks' not in inspector.get_table_names():
        return
    columns = {col['name'] for col in inspector.get_columns('resource_generation_tasks')}
    if 'audit_report' not in columns:
        db.session.execute(text('ALTER TABLE resource_generation_tasks ADD COLUMN audit_report JSON'))
        db.session.commit()

