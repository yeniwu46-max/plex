"""Flask应用程序入口"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.models import db
from app.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig
from app.routes import register_routes
from app.middleware.error_handler import register_error_handlers


def create_app(config_name='development'):
    """应用程序工厂函数"""
    
    # 选择配置
    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
    }
    
    config = config_map.get(config_name, DevelopmentConfig)
    
    # 创建Flask应用
    app = Flask(__name__)
    app.config.from_object(config)
    
    # 初始化扩展
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app)
    
    # 注册路由
    register_routes(app)
    
    # 注册错误处理器
    register_error_handlers(app, jwt)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        init_seed_data()
    
    return app


def init_seed_data():
    """初始化种子数据"""
    from app.models import Role, Permission, role_permissions

    # 检查是否已经初始化
    if Role.query.first():
        return

    # 创建角色
    student_role = Role(name='student', description='学生', color='green')
    teacher_role = Role(name='teacher', description='教师', color='orange')
    admin_role = Role(name='admin', description='管理员', color='purple')

    db.session.add_all([student_role, teacher_role, admin_role])
    db.session.flush()

    # 创建权限
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

    # 分配权限
    student_permissions = [0, 8, 6, 9]
    for idx in student_permissions:
        db.session.execute(role_permissions.insert().values(
            role_id=student_role.id,
            permission_id=permission_objs[idx].id
        ))

    teacher_permissions = [0, 1, 4, 6, 7, 9]
    for idx in teacher_permissions:
        db.session.execute(role_permissions.insert().values(
            role_id=teacher_role.id,
            permission_id=permission_objs[idx].id
        ))

    for perm in permission_objs:
        db.session.execute(role_permissions.insert().values(
            role_id=admin_role.id,
            permission_id=perm.id
        ))

    db.session.commit()


if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, port=5000)
