"""创建单个测试账号（不重置数据库）"""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite:///learning_system.db')

from app import create_app, db
from app.models import User, Class
from app.services.auth import AuthService

USERNAME = 'testuser001'
EMAIL = 'testuser001@example.com'
PASSWORD = 'test123456'
REAL_NAME = '测试用户001'
ROLE = 'student'


def main():
    app = create_app('development')

    with app.app_context():
        existing = User.query.filter_by(username=USERNAME).first()
        if existing:
            print('账号已存在：')
            print(f'  用户名: {existing.username}')
            print(f'  密码: {PASSWORD}（若此前由本脚本创建则为此密码）')
            print(f'  角色: {existing.role.name if existing.role else "?"}')
            print(f'  用户 ID: {existing.id}')
            return 0

        try:
            result = AuthService.register(
                username=USERNAME,
                email=EMAIL,
                password=PASSWORD,
                real_name=REAL_NAME,
                role=ROLE,
            )
            user = User.query.get(result['id'])
            cls = Class.query.first()
            if user and cls:
                user.class_id = cls.id
                user.level = 1
                user.total_points = 50
                db.session.commit()

            print('测试账号创建成功：')
            print(f'  用户名: {USERNAME}')
            print(f'  密码: {PASSWORD}')
            print(f'  邮箱: {EMAIL}')
            print(f'  姓名: {REAL_NAME}')
            print(f'  角色: {ROLE}')
            print(f'  用户 ID: {result["id"]}')
            if user and user.class_id:
                print(f'  班级 ID: {user.class_id}')
            return 0
        except Exception as exc:
            print(f'创建失败: {exc}', file=sys.stderr)
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
