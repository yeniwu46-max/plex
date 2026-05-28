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
    }
    for name, col_type in additions.items():
        if name in existing:
            continue
        db.session.execute(text(f'ALTER TABLE trial_question_progress ADD COLUMN {name} {col_type}'))
    db.session.commit()
