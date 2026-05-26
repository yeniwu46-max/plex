"""数据库初始化脚本"""
from app import create_app, db
from app.models import User, Role, Permission, RolePermission, Class, Achievement, UserAchievement, PointsLog, RankingCache, DailyQuest
from app.services.daily_quest import DEFAULT_DAILY_QUESTS

def init_db():
    """初始化数据库"""
    app = create_app('development')
    
    with app.app_context():
        # 删除所有表
        print("删除现有表...")
        db.drop_all()
        
        # 创建所有表
        print("创建新表...")
        db.create_all()
        
        # 插入初始数据
        print("插入初始数据...")
        
        # 创建角色
        student_role = Role(name='student', description='学生', color='green')
        teacher_role = Role(name='teacher', description='教师', color='orange')
        admin_role = Role(name='admin', description='管理员', color='purple')
        
        db.session.add_all([student_role, teacher_role, admin_role])
        db.session.flush()
        
        # 创建权限
        permissions = [
            Permission(name='view_users', description='查看用户', resource='users', action='read'),
            Permission(name='create_user', description='创建用户', resource='users', action='create'),
            Permission(name='edit_user', description='编辑用户', resource='users', action='update'),
            Permission(name='delete_user', description='删除用户', resource='users', action='delete'),
            Permission(name='manage_classes', description='管理班级', resource='classes', action='all'),
            Permission(name='manage_permissions', description='管理权限', resource='permissions', action='all'),
            Permission(name='view_achievements', description='查看成就', resource='achievements', action='read'),
            Permission(name='manage_achievements', description='管理成就', resource='achievements', action='all'),
            Permission(name='submit_assignment', description='提交作业', resource='assignments', action='create'),
            Permission(name='view_rankings', description='查看排名', resource='rankings', action='read'),
        ]
        
        db.session.add_all(permissions)
        db.session.flush()
        
        # 分配权限
        # 学生权限
        for perm in [permissions[0], permissions[8], permissions[6], permissions[9]]:
            rp = RolePermission(role_id=student_role.id, permission_id=perm.id)
            db.session.add(rp)
        
        # 教师权限
        for perm in [permissions[0], permissions[1], permissions[4], permissions[6], permissions[7], permissions[9]]:
            rp = RolePermission(role_id=teacher_role.id, permission_id=perm.id)
            db.session.add(rp)
        
        # 管理员权限（全部）
        for perm in permissions:
            rp = RolePermission(role_id=admin_role.id, permission_id=perm.id)
            db.session.add(rp)
        
        # 创建测试用户
        from werkzeug.security import generate_password_hash
        
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            real_name='管理员',
            role_id=admin_role.id
        )
        
        teacher_user = User(
            username='teacher001',
            email='teacher@example.com',
            password_hash=generate_password_hash('teacher123'),
            real_name='李老师',
            role_id=teacher_role.id
        )
        
        db.session.add_all([admin_user, teacher_user])
        db.session.flush()
        
        # 创建班级
        class1 = Class(
            name='2024级1班',
            description='2024年入学的一班',
            grade_level=1,
            teacher_id=teacher_user.id
        )
        
        db.session.add(class1)
        db.session.flush()
        
        # 创建学生
        for i in range(1, 6):
            student = User(
                username=f'student{i:03d}',
                email=f'student{i:03d}@example.com',
                password_hash=generate_password_hash('student123'),
                real_name=f'学生{i}',
                role_id=student_role.id,
                class_id=class1.id,
                level=1,
                total_points=i * 100
            )
            db.session.add(student)
        
        # 创建成就
        achievements = [
            Achievement(
                name='初心者',
                description='完成第一个课程',
                icon_url='/icons/newbie.png',
                rarity='common',
                condition_type='complete_course',
                condition_value=1
            ),
            Achievement(
                name='连续学习者',
                description='连续学习7天',
                icon_url='/icons/streak.png',
                rarity='rare',
                condition_type='consecutive_days',
                condition_value=7
            ),
        ]
        
        db.session.add_all(achievements)
        db.session.add_all([DailyQuest(**quest) for quest in DEFAULT_DAILY_QUESTS])
        db.session.commit()
        
        print("数据库初始化完成！")
        print("测试账户信息：")
        print("  管理员: admin / admin123")
        print("  教师: teacher001 / teacher123")
        print("  学生: student001 / student123 (学生001-005)")

if __name__ == '__main__':
    init_db()
