"""扩展成就目录并刷新班级排名缓存（可重复执行）"""
from app import create_app
from app.models import Achievement, Class, User, db
from app.services.incentive import IncentiveService

ACHIEVEMENTS = [
    {
        'name': '初心者',
        'description': '完成第一条每日委托',
        'rarity': 'common',
        'condition_type': 'complete_course',
        'condition_value': 1,
    },
    {
        'name': '连续学习者',
        'description': '连续探索 7 天',
        'rarity': 'rare',
        'condition_type': 'consecutive_days',
        'condition_value': 7,
    },
    {
        'name': '积分新星',
        'description': '累计获得 500 XP',
        'rarity': 'common',
        'condition_type': 'total_points',
        'condition_value': 500,
    },
    {
        'name': '星轨行者',
        'description': '达到 Lv.2',
        'rarity': 'rare',
        'condition_type': 'level',
        'condition_value': 2,
    },
    {
        'name': '试炼先锋',
        'description': '完成 1 次班级试炼',
        'rarity': 'epic',
        'condition_type': 'trials_completed',
        'condition_value': 1,
    },
    {
        'name': '委托达人',
        'description': '累计完成 10 条每日委托',
        'rarity': 'epic',
        'condition_type': 'daily_quests_completed',
        'condition_value': 10,
    },
    {
        'name': '深空传奇',
        'description': '累计获得 5000 XP',
        'rarity': 'legendary',
        'condition_type': 'total_points',
        'condition_value': 5000,
    },
]


def main():
    app = create_app()
    with app.app_context():
        for item in ACHIEVEMENTS:
            row = Achievement.query.filter_by(name=item['name']).first()
            if row:
                row.description = item['description']
                row.rarity = item['rarity']
                row.condition_type = item['condition_type']
                row.condition_value = item['condition_value']
            else:
                db.session.add(Achievement(**item))
        db.session.commit()

        classes = Class.query.all()
        for cls in classes:
            IncentiveService.refresh_class_ranking(cls.id)
            for student in User.query.filter_by(class_id=cls.id).all():
                IncentiveService.sync_user_level(student)
                IncentiveService.check_and_unlock_achievements(student.id)
        db.session.commit()
        print(f'成就目录: {Achievement.query.count()} 条；已刷新 {len(classes)} 个班级排名缓存。')


if __name__ == '__main__':
    main()
