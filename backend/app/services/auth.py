"""Account registration and login services."""
import re
import secrets
from flask import current_app
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from .base import BaseService
from .auth_security import normalize_email, validate_password, invalidate_sessions
from app.models import User, Role, db, OAuthIdentity


class AuthService(BaseService):
    @staticmethod
    def session(user):
        from app.utils.jwt_utils import create_tokens
        from .onboarding import OnboardingService
        tokens = create_tokens(user.id, {'username': user.username, 'role': user.role.name})
        if user.role.name == 'student':
            from flask_jwt_extended import decode_token
            from .learner_state import LearnerStateService
            LearnerStateService.append(user_id=user.id, kind='session_start', source_type='auth_session',
                source_id=decode_token(tokens['access_token'])['sid'], source_version='1',
                payload={'evidence_scope': 'session', 'concept_id': None})
            db.session.commit()
        return {**user.to_dict(), **tokens, **OnboardingService.account_fields(user.id), 'expiresIn': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())}

    @staticmethod
    def register(username, email, password, real_name, role='student'):
        if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{2,29}', username.strip()):
            raise ValueError('用户名需为 3–30 位字母、数字、下划线或短横线，以字母或数字开头')
        username = username.strip()
        email = normalize_email(email)
        validate_password(password)
        if not isinstance(real_name, str) or not 1 <= len(real_name.strip()) <= 50:
            raise ValueError('昵称需为 1–50 个字符')
        if role != 'student':
            raise ValueError('公开注册仅支持学生账号')
        if User.query.filter(or_(func.lower(User.username) == username.lower(), func.lower(User.email) == email)).first():
            raise ValueError('用户名或邮箱已被使用，请登录或找回密码')
        role_obj = Role.query.filter_by(name='student').first()
        if not role_obj:
            raise RuntimeError('Student role is missing')
        user = User(username=username, email=email, password_hash=generate_password_hash(password),
                    real_name=real_name.strip(), role_id=role_obj.id)
        db.session.add(user)
        try:
            from .onboarding import OnboardingService
            OnboardingService.enroll(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError('用户名或邮箱已被使用，请登录或找回密码') from None
        return AuthService.session(user)

    @staticmethod
    def login(username, password):
        if not isinstance(username, str) or not isinstance(password, str) or len(username)>100 or len(password)>128:
            raise ValueError('用户名、邮箱或密码不正确')
        account = username.strip().lower()
        user = User.query.filter(or_(func.lower(User.username) == account, func.lower(User.email) == account)).first()
        # Run a password hash check even for unknown accounts.
        from .auth_security import DUMMY_PASSWORD_HASH
        valid = check_password_hash(user.password_hash if user else DUMMY_PASSWORD_HASH, password)
        if not user or not valid or user.status != 'active' or password.startswith(('oauth:google:', 'oauth:github:')):
            raise ValueError('用户名、邮箱或密码不正确，或账号不可用')
        return AuthService.session(user)

    @staticmethod
    def login_or_register_oauth(provider, provider_user_id, email, display_name=None, avatar_url=None):
        email = normalize_email(email)
        username = f'{provider}_{str(provider_user_id)[:32]}'[:50]
        identity_key = f'{provider}:{provider_user_id}'
        if len(identity_key) > 160:
            raise ValueError('第三方身份无效')
        linked = db.session.get(OAuthIdentity, identity_key)
        user = db.session.get(User, linked.user_id) if linked else None
        if not user:
            if User.query.filter(func.lower(User.email) == email).first():
                raise ValueError('该邮箱已有账号，请使用密码登录或找回密码')
            if User.query.filter(func.lower(User.username) == username.lower()).first():
                username = f'{provider}_{secrets.token_hex(12)}'
            role = Role.query.filter_by(name='student').first()
            user = User(username=username, email=email, password_hash=generate_password_hash(secrets.token_urlsafe(48)),
                        real_name=(display_name or username)[:50], avatar_url=avatar_url, role_id=role.id)
            db.session.add(user)
            try:
                db.session.flush()
                db.session.add(OAuthIdentity(identity_key=identity_key, user_id=user.id))
                from .onboarding import OnboardingService
                OnboardingService.enroll(user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                raise ValueError('账号已存在，请使用密码登录') from None
        if user.email.lower() != email or user.status != 'active':
            raise ValueError('第三方身份与账号不匹配，请使用密码登录')
        return AuthService.session(user)

    @staticmethod
    def verify_password(password_hash, password):
        return check_password_hash(password_hash, password)

    @staticmethod
    def change_password(user_id, old_password, new_password):
        validate_password(new_password)
        user = db.session.get(User, user_id)
        if not user or not isinstance(old_password,str) or not check_password_hash(user.password_hash, old_password):
            raise ValueError('旧密码错误')
        invalidate_sessions(user.id)
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
