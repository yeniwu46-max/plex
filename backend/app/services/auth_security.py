"""Validation, persistent throttling, session revocation and password recovery."""
from datetime import timedelta
from email.message import EmailMessage
import hashlib
import hmac
import re
import secrets
import smtplib
import ssl
import time
from urllib.parse import quote

from flask import current_app, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from app.models import AuthRateLimit, AuthSessionState, AuthToken, User, db
from app.utils.time import utc_now

DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_urlsafe(32))


def validate_password(value):
    if not isinstance(value, str) or not 8 <= len(value) <= 128 or not re.search(r'[A-Za-z]', value) or not re.search(r'\d', value):
        raise ValueError('密码需为 8–128 位，至少包含字母和数字')
    if value.startswith(('oauth:google:', 'oauth:github:')):
        raise ValueError('请使用新的个人密码，不可使用旧版第三方登录默认密码')
    return value


def normalize_email(value):
    if not isinstance(value, str):
        raise ValueError('请输入有效的邮箱地址')
    value = value.strip().lower()
    if len(value) > 100 or not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+', value) or value.endswith('.local'):
        raise ValueError('请输入可接收邮件的有效邮箱地址')
    return value


def hash_token(value):
    return hashlib.sha256(value.encode()).hexdigest()


def session_version(user_id):
    state = db.session.get(AuthSessionState, int(user_id))
    return state.version if state else 0


def ensure_state(user_id):
    if db.session.get(AuthSessionState, user_id) is None:
        db.session.add(AuthSessionState(user_id=user_id, version=0))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def invalidate_sessions(user_id):
    ensure_state(user_id)
    AuthSessionState.query.filter_by(user_id=user_id).update({AuthSessionState.version: AuthSessionState.version + 1})


def token_revoked(payload):
    try:
        user = db.session.get(User, int(payload['sub']))
    except (ValueError, TypeError, KeyError):
        return True
    if not user or user.status != 'active' or payload.get('auth_version', 0) != session_version(user.id):
        return True
    key = payload.get('sid') or payload['jti']
    return db.session.get(AuthToken, hash_token('session:' + key)) is not None


def revoke_session(payload):
    key = hash_token('session:' + (payload.get('sid') or payload['jti']))
    if db.session.get(AuthToken, key) is None:
        db.session.add(AuthToken(token_hash=key, user_id=int(payload['sub']), purpose='revoked', version=0,
                                 expires_at=utc_now() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']))


def throttle(action, identity='', limit=10, seconds=900):
    if not current_app.config.get('AUTH_RATE_LIMIT_ENABLED', True):
        return False
    now = utc_now()
    # Fixed windows and atomic increments work across processes on SQLite/MySQL.
    raw = f'{action}:{identity}:{int(time.time()) // seconds}'
    key = hmac.new(current_app.config['SECRET_KEY'].encode(), raw.encode(), hashlib.sha256).hexdigest()
    AuthRateLimit.query.filter(AuthRateLimit.expires_at < now).delete(synchronize_session=False)
    AuthToken.query.filter(AuthToken.expires_at < now).delete(synchronize_session=False)
    db.session.commit()
    if db.session.get(AuthRateLimit, key) is None:
        db.session.add(AuthRateLimit(key_hash=key, attempts=0, expires_at=now + timedelta(seconds=seconds)))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    changed = AuthRateLimit.query.filter(AuthRateLimit.key_hash == key, AuthRateLimit.attempts < limit).update(
        {AuthRateLimit.attempts: AuthRateLimit.attempts + 1}, synchronize_session=False)
    db.session.commit()
    return not changed


def mail_ready():
    return bool(current_app.config.get('SMTP_HOST') and current_app.config.get('SMTP_USER') and current_app.config.get('SMTP_PASSWORD'))


def send_reset_mail(email, token):
    config = current_app.config
    url = config['FRONTEND_BASE_URL'].rstrip('/') + '/reset-password#token=' + quote(token)
    message = EmailMessage()
    message['Subject'] = 'PLEX 密码重置'
    message['From'] = config['SMTP_USER']
    message['To'] = email
    message.set_content(f'你正在申请重置 PLEX 密码。请在 15 分钟内打开以下链接：\n\n{url}\n\n链接仅能使用一次。如果不是你发起的申请，请忽略此邮件。')
    with smtplib.SMTP_SSL(config['SMTP_HOST'], config['SMTP_PORT'], timeout=15, context=ssl.create_default_context()) as smtp:
        smtp.login(config['SMTP_USER'], config['SMTP_PASSWORD'])
        smtp.send_message(message)


def request_reset(email):
    email = normalize_email(email)
    user = User.query.filter(func.lower(User.email) == email, User.status == 'active').first()
    if not user:
        return
    token = secrets.token_urlsafe(32)
    ensure_state(user.id)
    row = AuthToken(token_hash=hash_token(token), user_id=user.id, purpose='reset', version=session_version(user.id),
                    expires_at=utc_now() + timedelta(minutes=15))
    db.session.add(row)
    try:
        send_reset_mail(email, token)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # No token, password, SMTP response or email address in application logs.
        current_app.logger.error('Password recovery email delivery failed; check SMTP configuration.')


def finish_reset(token, password):
    validate_password(password)
    if not isinstance(token, str) or not 20 <= len(token) <= 200:
        raise ValueError('重置链接无效或已过期，请重新申请')
    row = db.session.get(AuthToken, hash_token(token))
    if not row or row.purpose != 'reset' or row.expires_at <= utc_now():
        raise ValueError('重置链接无效或已过期，请重新申请')
    user = db.session.get(User, row.user_id)
    if not user or user.status != 'active':
        raise ValueError('重置链接无效或已过期，请重新申请')
    changed = AuthSessionState.query.filter_by(user_id=user.id, version=row.version).update(
        {AuthSessionState.version: AuthSessionState.version + 1}, synchronize_session=False)
    if not changed:
        db.session.rollback()
        raise ValueError('重置链接已使用，请重新申请')
    user.password_hash = generate_password_hash(password)
    AuthToken.query.filter_by(user_id=user.id, purpose='reset').delete(synchronize_session=False)
    db.session.commit()
