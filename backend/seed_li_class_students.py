"""在李老师（teacher001）的班级中创建 10 名测试 Explorer（不重置数据库）。"""
import os
import sys
from datetime import date, datetime, timedelta

os.environ.setdefault('DATABASE_URL', 'sqlite:///instance/learning_system.db')

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Class, DailyQuest, PointsLog, RankingCache, Role, User, UserDailyQuest

TEACHER_USERNAME = 'teacher001'
PASSWORD = 'student123'

STUDENTS = [
    ('explorer01', '张明', 'explorer01@example.com', 4, 2850, 12),
    ('explorer02', '李华', 'explorer02@example.com', 4, 2680, 10),
    ('explorer03', '王芳', 'explorer03@example.com', 3, 2420, 8),
    ('explorer04', '刘洋', 'explorer04@example.com', 3, 2210, 7),
    ('explorer05', '陈静', 'explorer05@example.com', 3, 1980, 6),
    ('explorer06', '杨帆', 'explorer06@example.com', 2, 1760, 5),
    ('explorer07', '赵雪', 'explorer07@example.com', 2, 1520, 4),
    ('explorer08', '周磊', 'explorer08@example.com', 2, 1280, 3),
    ('explorer09', '吴婷', 'explorer09@example.com', 1, 940, 2),
    ('explorer10', '孙浩', 'explorer10@example.com', 1, 620, 1),
]


def seed_daily_quests(user_id: int, quests: list, completion_pattern: list[int]) -> None:
    """completion_pattern: 每天完成的委托项数（0-4），长度 7 表示近 7 天。"""
    today = date.today()
    for day_offset, completed_count in enumerate(completion_pattern):
        quest_date = today - timedelta(days=len(completion_pattern) - 1 - day_offset)
        done = max(0, min(completed_count, len(quests)))
        for idx, quest in enumerate(quests):
            record = UserDailyQuest(
                user_id=user_id,
                quest_id=quest.id,
                quest_date=quest_date,
                current=quest.total if idx < done else 0,
                completed_at=datetime.utcnow() if idx < done else None,
            )
            db.session.add(record)


def seed_points_logs(user_id: int, base_points: int) -> None:
    now = datetime.utcnow()
    entries = [
        (base_points // 10, 'daily_quest:morning-launch', 1),
        (base_points // 8, 'complete_course', None),
        (base_points // 12, 'daily_quest:trial-challenge', 3),
    ]
    for idx, (pts, reason, related) in enumerate(entries):
        db.session.add(
            PointsLog(
                user_id=user_id,
                points=pts,
                reason=reason,
                related_id=related,
                created_at=now - timedelta(hours=idx * 5 + 1),
            )
        )


def main() -> int:
    app = create_app('development')

    with app.app_context():
        teacher = User.query.filter_by(username=TEACHER_USERNAME).first()
        if not teacher:
            print(f'未找到教师账号 {TEACHER_USERNAME}，请先运行 init_db 或启动后端初始化。', file=sys.stderr)
            return 1

        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            print('未找到 student 角色。', file=sys.stderr)
            return 1

        target_class = Class.query.filter_by(teacher_id=teacher.id).order_by(Class.id.asc()).first()
        if not target_class:
            target_class = Class(
                name='水星轨站·探索一班',
                description='PLEX 水星轨站领航班级',
                grade_level=1,
                teacher_id=teacher.id,
            )
            db.session.add(target_class)
            db.session.flush()
            print(f'已创建班级: {target_class.name} (id={target_class.id})')

        quests = (
            DailyQuest.query.filter_by(is_active=True)
            .order_by(DailyQuest.sort_order.asc(), DailyQuest.id.asc())
            .all()
        )
        if not quests:
            print('未找到每日委托定义，请先启动后端或执行 init_db。', file=sys.stderr)
            return 1

        current_week = f'{datetime.now().year}-w{datetime.now().isocalendar()[1]:02d}'
        patterns = [
            [4, 4, 3, 4, 2, 3, 4],
            [4, 3, 4, 3, 4, 4, 3],
            [3, 3, 2, 3, 3, 2, 3],
            [3, 2, 3, 2, 2, 3, 2],
            [2, 3, 2, 3, 2, 2, 3],
            [2, 2, 1, 2, 2, 1, 2],
            [2, 1, 2, 1, 1, 2, 1],
            [1, 2, 1, 2, 1, 1, 2],
            [1, 1, 0, 1, 1, 0, 1],
            [0, 1, 1, 0, 1, 0, 1],
        ]

        created = []
        skipped = []

        for idx, (username, real_name, email, level, points, streak) in enumerate(STUDENTS):
            if User.query.filter_by(username=username).first():
                skipped.append(username)
                continue

            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(PASSWORD),
                real_name=real_name,
                role_id=student_role.id,
                class_id=target_class.id,
                level=level,
                total_points=points,
                consecutive_days=streak,
                status='active',
            )
            db.session.add(user)
            db.session.flush()

            seed_daily_quests(user.id, quests, patterns[idx % len(patterns)])
            seed_points_logs(user.id, points)

            db.session.add(
                RankingCache(
                    class_id=target_class.id,
                    user_id=user.id,
                    rank=idx + 1,
                    points=points,
                    level=level,
                    week=current_week,
                )
            )
            created.append((username, real_name, user.id))

        student_count = User.query.filter_by(class_id=target_class.id, role_id=student_role.id).count()
        target_class.student_count = student_count
        db.session.commit()

        print(f'班级: {target_class.name} (id={target_class.id})，教师: {teacher.real_name} ({TEACHER_USERNAME})')
        print(f'当前班级学生总数: {student_count}')
        if created:
            print('\n新创建账号（密码均为 student123）：')
            for username, real_name, uid in created:
                print(f'  {username:12} {real_name:6} id={uid}')
        if skipped:
            print('\n已跳过（用户名已存在）：', ', '.join(skipped))
        if not created and not skipped:
            print('未创建任何学生。')
        return 0 if created or skipped else 1


if __name__ == '__main__':
    raise SystemExit(main())
