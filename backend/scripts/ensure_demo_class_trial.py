# -*- coding: utf-8 -*-
"""为学生演示账号确保存在教师发布的进行中班级试炼（幂等）。"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

_SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_ROOT))

from app import create_app
from app.models import Class, Role, Trial, User, db
from app.services.question_generator import QuestionGenerator
from app.utils.time import utc_now

DEMO_TRIAL_TITLE = 'Python 入门·班级训练'
DEMO_CLASS_NAME = '水星轨站·探索一班'
TEACHER_USERNAME = 'teacher001'
STUDENT_USERNAMES = ('student001',)


def ensure_demo_class_trial() -> None:
    """开发环境启动时为演示学生确保有可参与的班级试炼。"""
    teacher = User.query.filter_by(username=TEACHER_USERNAME).first()
    student_role = Role.query.filter_by(name='student').first()
    if not teacher or not student_role:
        return

    target_class = Class.query.filter_by(teacher_id=teacher.id, name=DEMO_CLASS_NAME).first()
    if not target_class:
        target_class = Class.query.filter_by(teacher_id=teacher.id).order_by(Class.id.asc()).first()
    if not target_class:
        target_class = Class(
            name=DEMO_CLASS_NAME,
            description='PLEX 演示班级',
            grade_level=1,
            teacher_id=teacher.id,
        )
        db.session.add(target_class)
        db.session.flush()

    for username in STUDENT_USERNAMES:
        user = User.query.filter_by(username=username).first()
        if user and not user.class_id:
            user.class_id = target_class.id

    now = utc_now()
    trial = (
        Trial.query.filter_by(class_id=target_class.id, title=DEMO_TRIAL_TITLE)
        .order_by(Trial.id.desc())
        .first()
    )
    if not trial:
        trial = Trial(
            class_id=target_class.id,
            teacher_id=teacher.id,
            title=DEMO_TRIAL_TITLE,
            trial_type='solo',
            knowledge_key='intro',
            difficulty=45,
            duration_minutes=45,
            status='running',
            reward_points=30,
            starts_at=now - timedelta(hours=2),
            ends_at=now + timedelta(days=7),
        )
        trial.set_knowledge_keys(['intro', 'var', 'loop'])
        db.session.add(trial)
        db.session.flush()
    else:
        if trial.status != 'running':
            trial.status = 'running'
        trial.starts_at = trial.starts_at or now - timedelta(hours=2)
        trial.ends_at = trial.ends_at or now + timedelta(days=7)
        trial.reward_points = max(int(trial.reward_points or 0), 30)
        trial.difficulty = min(int(trial.difficulty or 45), 80)

    QuestionGenerator.ensure_for_trial(trial)
    student_count = User.query.filter_by(class_id=target_class.id, role_id=student_role.id).count()
    target_class.student_count = student_count
    db.session.commit()


def main() -> None:
    app = create_app()
    with app.app_context():
        ensure_demo_class_trial()
        print('Demo class trial ensured for student001.')


if __name__ == '__main__':
    main()
