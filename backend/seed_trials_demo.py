"""为 teacher001 班级插入演示试炼（不重置数据库）。"""
import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault('DATABASE_URL', 'sqlite:///learning_system.db')

from app import create_app, db
from app.models import Class, Trial, TrialParticipation, User


def main() -> int:
    app = create_app('development')
    with app.app_context():
        db.create_all()

        teacher = User.query.filter_by(username='teacher001').first()
        if not teacher:
            print('未找到 teacher001', file=sys.stderr)
            return 1

        target_class = Class.query.filter_by(teacher_id=teacher.id).order_by(Class.id.asc()).first()
        if not target_class:
            print('李老师暂无班级', file=sys.stderr)
            return 1

        students = User.query.filter_by(class_id=target_class.id).limit(10).all()
        now = datetime.utcnow()

        demos = [
            {
                'title': '动态规划挑战赛',
                'trial_type': 'solo',
                'knowledge_key': 'dp',
                'difficulty': 78,
                'duration_minutes': 60,
                'status': 'running',
                'reward_points': 40,
                'starts_at': now - timedelta(hours=2),
                'ends_at': now + timedelta(hours=4),
            },
            {
                'title': '图论专项训练',
                'trial_type': 'team',
                'knowledge_key': 'graph',
                'difficulty': 62,
                'duration_minutes': 90,
                'status': 'running',
                'reward_points': 35,
                'starts_at': now - timedelta(hours=1),
                'ends_at': now + timedelta(hours=6),
            },
            {
                'title': '深渊试炼：递归迷宫',
                'trial_type': 'abyss',
                'knowledge_key': 'algo',
                'difficulty': 92,
                'duration_minutes': 120,
                'status': 'ended',
                'reward_points': 50,
                'starts_at': now - timedelta(days=2),
                'ends_at': now - timedelta(days=1),
            },
        ]

        created = 0
        for item in demos:
            exists = Trial.query.filter_by(class_id=target_class.id, title=item['title']).first()
            if exists:
                continue
            trial = Trial(class_id=target_class.id, teacher_id=teacher.id, **item)
            db.session.add(trial)
            db.session.flush()

            for idx, student in enumerate(students[:6]):
                status = 'completed' if idx < 3 and trial.status == 'running' else ('joined' if idx < 5 else None)
                if not status:
                    continue
                db.session.add(
                    TrialParticipation(
                        trial_id=trial.id,
                        user_id=student.id,
                        status=status,
                        score=70 + idx * 5 if status == 'completed' else 0,
                        completed_at=now if status == 'completed' else None,
                    )
                )
            created += 1

        db.session.commit()
        total = Trial.query.filter_by(class_id=target_class.id).count()
        print(f'班级 {target_class.name} (id={target_class.id}) 试炼总数: {total}，本次新增: {created}')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
