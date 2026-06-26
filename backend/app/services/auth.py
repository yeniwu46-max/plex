"""认证相关服务"""
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from datetime import datetime, timedelta
from sqlalchemy import or_
from .base import BaseService
from app.models import User, Role, db


class AuthService(BaseService):
    """认证服务"""

    @staticmethod
    def register(username, email, password, real_name, role='student'):
        """
        用户注册
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            real_name: 真实姓名
            role: 角色 (student | teacher)
            
        Returns:
            dict: 用户信息和Token
            
        Raises:
            Exception: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            raise Exception('用户名已存在')
        
        # 检查邮箱是否已存在
        if User.query.filter_by(email=email).first():
            raise Exception('邮箱已存在')
        
        # 获取角色
        role_obj = Role.query.filter_by(name=role).first()
        if not role_obj:
            raise Exception('角色不存在')
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            real_name=real_name,
            role_id=role_obj.id
        )
        
        db.session.add(user)
        db.session.commit()
        
        # 创建Token
        from app.utils.jwt_utils import create_tokens
        tokens = create_tokens(
            identity=user.id,
            additional_claims={
                'username': user.username,
                'role': user.role.name
            }
        )
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'real_name': user.real_name,
            'role': user.role.name,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
        }

    @staticmethod
    def login(username, password):
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            dict: 用户信息和Token
            
        Raises:
            Exception: 用户不存在或密码错误
        """
        user = User.query.filter(or_(User.username == username, User.email == username)).first()
        
        if not user:
            raise Exception('用户不存在')
        
        if not check_password_hash(user.password_hash, password):
            raise Exception('密码错误')
        
        if user.status == 'deleted':
            raise Exception('用户已被删除')
        
        if user.status == 'frozen':
            raise Exception('用户已被冻结')
        
        # 创建Token
        from app.utils.jwt_utils import create_tokens
        tokens = create_tokens(
            identity=user.id,
            additional_claims={
                'username': user.username,
                'role': user.role.name
            }
        )
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'real_name': user.real_name,
            'role': user.role.name,
            'level': user.level,
            'total_points': user.total_points,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expiresIn': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()),
        }

    @staticmethod
    def login_or_register_oauth(provider, provider_user_id, email, display_name=None, avatar_url=None):
        """
        Sign in with an OAuth identity.

        The current schema does not have a separate linked-account table, so the
        stable mapping is email first, then a provider-prefixed username.
        """
        normalized_email = (email or '').strip().lower()
        if not normalized_email:
            normalized_email = f'{provider_user_id}@{provider}.oauth.local'

        user = User.query.filter_by(email=normalized_email).first()
        if not user:
            role_obj = Role.query.filter_by(name='student').first()
            if not role_obj:
                raise Exception('角色不存在')

            base_username = f'{provider}_{str(provider_user_id)[:32]}'
            username = base_username[:50]
            suffix = 1
            while User.query.filter_by(username=username).first():
                suffix += 1
                username = f'{base_username[:45]}_{suffix}'

            user = User(
                username=username,
                email=normalized_email,
                password_hash=generate_password_hash(f'oauth:{provider}:{provider_user_id}'),
                real_name=(display_name or normalized_email.split('@')[0])[:50],
                avatar_url=avatar_url,
                role_id=role_obj.id,
            )
            db.session.add(user)
            db.session.commit()
        elif avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            db.session.commit()

        if user.status == 'deleted':
            raise Exception('用户已被删除')
        if user.status == 'frozen':
            raise Exception('用户已被冻结')

        from app.utils.jwt_utils import create_tokens
        tokens = create_tokens(
            identity=user.id,
            additional_claims={
                'username': user.username,
                'role': user.role.name
            }
        )

        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'real_name': user.real_name,
            'role': user.role.name,
            'level': user.level,
            'total_points': user.total_points,
            'avatar_url': user.avatar_url,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'expiresIn': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()),
        }

    @staticmethod
    def verify_password(password_hash, password):
        """验证密码"""
        return check_password_hash(password_hash, password)

    @staticmethod
    def change_password(user_id, old_password, new_password):
        """
        修改密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Raises:
            Exception: 旧密码错误
        """
        user = db.session.get(User, user_id)
        
        if not user:
            raise Exception('用户不存在')
        
        if not check_password_hash(user.password_hash, old_password):
            raise Exception('旧密码错误')
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
