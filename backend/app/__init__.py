"""Flask application factory."""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from app.middleware.error_handler import register_error_handlers
from app.models import db
from app.routes import register_routes


def init_seed_data():
    """Create baseline roles and permissions when the database is empty."""
    from app.models import Permission, Role, role_permissions

    if Role.query.first():
        return

    student_role = Role(name='student', description='学生', color='green')
    teacher_role = Role(name='teacher', description='教师', color='orange')
    admin_role = Role(name='admin', description='管理员', color='purple')

    db.session.add_all([student_role, teacher_role, admin_role])
    db.session.flush()

    permissions_data = [
        {'name': 'view_users', 'description': '查看用户', 'resource': 'users', 'action': 'read'},
        {'name': 'create_user', 'description': '创建用户', 'resource': 'users', 'action': 'create'},
        {'name': 'edit_user', 'description': '编辑用户', 'resource': 'users', 'action': 'update'},
        {'name': 'delete_user', 'description': '删除用户', 'resource': 'users', 'action': 'delete'},
        {'name': 'manage_classes', 'description': '管理班级', 'resource': 'classes', 'action': 'all'},
        {'name': 'manage_permissions', 'description': '管理权限', 'resource': 'permissions', 'action': 'all'},
        {'name': 'view_achievements', 'description': '查看成就', 'resource': 'achievements', 'action': 'read'},
        {'name': 'manage_achievements', 'description': '管理成就', 'resource': 'achievements', 'action': 'all'},
        {'name': 'submit_assignment', 'description': '提交作业', 'resource': 'assignments', 'action': 'create'},
        {'name': 'view_rankings', 'description': '查看排名', 'resource': 'rankings', 'action': 'read'},
    ]

    permission_objs = []
    for perm_data in permissions_data:
        perm = Permission(**perm_data)
        db.session.add(perm)
        permission_objs.append(perm)

    db.session.flush()

    for idx in [0, 8, 6, 9]:
        db.session.execute(
            role_permissions.insert().values(role_id=student_role.id, permission_id=permission_objs[idx].id)
        )

    for idx in [0, 1, 2, 3, 6, 7, 9]:
        db.session.execute(
            role_permissions.insert().values(role_id=teacher_role.id, permission_id=permission_objs[idx].id)
        )

    for perm in permission_objs:
        db.session.execute(role_permissions.insert().values(role_id=admin_role.id, permission_id=perm.id))

    db.session.commit()


def sync_teacher_role_permissions():
    """将教师角色权限与定案对齐（已有库升级时调用）。"""
    from app.models import Permission, Role, role_permissions

    teacher_role = Role.query.filter_by(name='teacher').first()
    if not teacher_role:
        return

    desired = {
        'view_users',
        'create_user',
        'edit_user',
        'delete_user',
        'view_achievements',
        'manage_achievements',
        'view_rankings',
    }
    remove = {'manage_classes', 'manage_permissions'}

    perm_by_name = {p.name: p for p in Permission.query.all()}
    current = {p.name for p in teacher_role.permissions}

    for name in remove:
        perm = perm_by_name.get(name)
        if perm and name in current:
            db.session.execute(
                role_permissions.delete().where(
                    role_permissions.c.role_id == teacher_role.id,
                    role_permissions.c.permission_id == perm.id,
                )
            )

    for name in desired:
        perm = perm_by_name.get(name)
        if perm and name not in current:
            db.session.execute(
                role_permissions.insert().values(role_id=teacher_role.id, permission_id=perm.id)
            )

    db.session.commit()


def ensure_dev_login_users():
    """Upsert default development login accounts used by QUICKSTART and tests."""
    from werkzeug.security import generate_password_hash

    from app.models import Role, User

    admin_role = Role.query.filter_by(name='admin').first()
    teacher_role = Role.query.filter_by(name='teacher').first()
    student_role = Role.query.filter_by(name='student').first()
    if not admin_role or not teacher_role or not student_role:
        return

    defaults = [
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'password': 'admin123',
            'real_name': '管理员',
            'role_id': admin_role.id,
        },
        {
            'username': 'teacher001',
            'email': 'teacher@example.com',
            'password': 'teacher123',
            'real_name': '李老师',
            'role_id': teacher_role.id,
        },
        {
            'username': 'student001',
            'email': 'student001@example.com',
            'password': 'student123',
            'real_name': '学生1',
            'role_id': student_role.id,
        },
    ]

    for item in defaults:
        user = User.query.filter_by(username=item['username']).first()
        if not user:
            user = User(username=item['username'])
            db.session.add(user)
        user.email = item['email']
        user.password_hash = generate_password_hash(item['password'])
        user.real_name = item['real_name']
        user.role_id = item['role_id']
        if user.status == 'deleted':
            user.status = 'active'

    db.session.commit()


def create_app(config_name='development'):
    """Create and configure a Flask application."""
    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
    }
    config = config_map.get(config_name, DevelopmentConfig)

    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app)

    register_routes(app)
    register_error_handlers(app, jwt)

    with app.app_context():
        db.create_all()
        from app.utils.db_migrate import ensure_trial_progress_columns

        ensure_trial_progress_columns()
        init_seed_data()
        sync_teacher_role_permissions()
        ensure_dev_login_users()
        from app.services.daily_quest import DailyQuestService

        DailyQuestService.ensure_default_quests()

    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, port=5000)
