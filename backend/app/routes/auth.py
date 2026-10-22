"""认证路由"""
import json
import secrets
import hmac
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, redirect, request, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, decode_token, create_access_token
from itsdangerous import BadSignature, URLSafeTimedSerializer
from app.services import AuthService
from app.models import User, db
from app.services.auth_security import (mail_ready, request_reset, finish_reset, throttle, revoke_session, session_version)

from app.utils.response import success_response, error_response

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


def _frontend_oauth_redirect(params):
    base = current_app.config.get('FRONTEND_BASE_URL', 'http://localhost:5180').rstrip('/')
    response = redirect(f"{base}/oauth/callback#{urlencode(params)}")
    response.delete_cookie('plex_oauth_state', path='/api/v1/auth/oauth')
    response.headers['Cache-Control'] = 'no-store'
    return response


def _oauth_redirect_uri(provider):
    configured = current_app.config.get(f'{provider.upper()}_REDIRECT_URI')
    if configured:
        return configured
    return url_for('auth.oauth_callback', provider=provider, _external=True)


def _oauth_config(provider):
    configs = {
        'google': {
            'client_id': current_app.config.get('GOOGLE_CLIENT_ID'),
            'client_secret': current_app.config.get('GOOGLE_CLIENT_SECRET'),
            'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'scope': 'openid email profile',
        },
        'github': {
            'client_id': current_app.config.get('GITHUB_CLIENT_ID'),
            'client_secret': current_app.config.get('GITHUB_CLIENT_SECRET'),
            'authorize_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'scope': 'read:user user:email',
        },
    }
    return configs.get(provider)


def _state_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='oauth-state')


def _provider_profile(provider, access_token):
    headers = {'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
    if provider == 'google':
        resp = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            'id': data.get('sub'),
            'email': data.get('email') if data.get('email_verified') is True else None,
            'name': data.get('name'),
            'avatar_url': data.get('picture'),
        }

    resp = requests.get('https://api.github.com/user', headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    emails_resp = requests.get('https://api.github.com/user/emails', headers=headers, timeout=10)
    emails_resp.raise_for_status()
    verified = [item for item in emails_resp.json() if item.get('verified')]
    primary = next((item for item in verified if item.get('primary')), verified[0] if verified else None)
    email = primary.get('email') if primary else None
    return {
        'id': data.get('id'),
        'email': email,
        'name': data.get('name') or data.get('login'),
        'avatar_url': data.get('avatar_url'),
    }


@auth_bp.route('/oauth/<provider>', methods=['GET'])
def oauth_start(provider):
    """Start a Google/GitHub OAuth login."""
    config = _oauth_config(provider)
    if not config:
        return _frontend_oauth_redirect({'error': '暂不支持该第三方登录方式'})

    if not config['client_id'] or not config['client_secret']:
        return _frontend_oauth_redirect({'error': f'{provider} 登录尚未配置 Client ID/Secret'})

    state = _state_serializer().dumps({
        'provider': provider,
        'redirect': safe_redirect(request.args.get('redirect')),
        'nonce': secrets.token_urlsafe(24),
    })
    params = {
        'client_id': config['client_id'],
        'redirect_uri': _oauth_redirect_uri(provider),
        'scope': config['scope'],
        'state': state,
        'response_type': 'code',
    }
    if provider == 'google':
        params['access_type'] = 'offline'
        params['prompt'] = 'select_account'
    response = redirect(f"{config['authorize_url']}?{urlencode(params)}")
    response.set_cookie('plex_oauth_state', state, max_age=600, httponly=True, secure=request.is_secure,
                        samesite='Lax', path='/api/v1/auth/oauth')
    return response


@auth_bp.route('/oauth/<provider>/callback', methods=['GET'])
def oauth_callback(provider):
    """Handle Google/GitHub OAuth callback and hand the JWT session to Vue."""
    config = _oauth_config(provider)
    if not config:
        return _frontend_oauth_redirect({'error': '暂不支持该第三方登录方式'})

    if request.args.get('error'):
        return _frontend_oauth_redirect({'error': request.args.get('error_description') or request.args['error']})

    try:
        raw = request.args.get('state', '')
        cookie = request.cookies.get('plex_oauth_state', '')
        if not raw or not cookie or not hmac.compare_digest(raw, cookie):
            raise BadSignature('Browser state missing')
        state = _state_serializer().loads(raw, max_age=600)
    except BadSignature:
        return _frontend_oauth_redirect({'error': '第三方登录状态校验失败'})

    if state.get('provider') != provider:
        return _frontend_oauth_redirect({'error': '第三方登录状态不匹配'})

    code = request.args.get('code')
    if not code:
        return _frontend_oauth_redirect({'error': '第三方登录缺少授权码'})

    try:
        token_resp = requests.post(
            config['token_url'],
            data={
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'code': code,
                'redirect_uri': _oauth_redirect_uri(provider),
                'grant_type': 'authorization_code',
            },
            headers={'Accept': 'application/json'},
            timeout=10,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get('access_token')
        if not access_token:
            return _frontend_oauth_redirect({'error': '第三方登录未返回 access_token'})

        profile = _provider_profile(provider, access_token)
        if not profile.get('id') or not profile.get('email'):
            return _frontend_oauth_redirect({'error': '第三方登录未返回用户标识'})

        session = AuthService.login_or_register_oauth(
            provider=provider,
            provider_user_id=profile['id'],
            email=profile.get('email'),
            display_name=profile.get('name'),
            avatar_url=profile.get('avatar_url'),
        )
        return _frontend_oauth_redirect({
            'session': json.dumps(session, ensure_ascii=False),
            'redirect': state.get('redirect') or '/',
        })
    except Exception:
        db.session.rollback()
        current_app.logger.error('OAuth login failed for %s', provider)
        return _frontend_oauth_redirect({'error': '第三方登录未完成，请使用密码登录或稍后重试'})


def safe_redirect(value):
    return value if isinstance(value, str) and value.startswith('/') and not value.startswith('//') and '\\' not in value and not any(ord(c)<32 for c in value) else '/'


@auth_bp.before_request
def limit_auth_requests():
    if request.method == 'POST' and request.endpoint in {'auth.login', 'auth.register', 'auth.forgot_password', 'auth.reset_password'}:
        action = request.endpoint.split('.')[-1]
        if (request.content_length or 0) > 8192:
            return error_response('请求内容过长', 40001)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error_response('请提交有效的 JSON 对象', 40001)
        identity = data.get('email') if action == 'forgot_password' else data.get('username')
        limited = throttle(action + ':ip', request.remote_addr or 'unknown', 60 if action == 'login' else 15)
        if isinstance(identity, str):
            limited = throttle(action + ':account', identity.strip().lower()[:100], 15 if action == 'login' else 5) or limited
        if limited:
            response, status = error_response('操作过于频繁，请 15 分钟后重试', 42901, None, 429)
            response.headers['Retry-After'] = '900'
            return response, status


@auth_bp.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@auth_bp.get('/capabilities')
def capabilities():
    return success_response({'registration_enabled': True, 'password_reset_enabled': mail_ready(),
        'support_email': current_app.config.get('AUTH_SUPPORT_EMAIL', ''),
        'oauth_providers': [name for name in ('google', 'github') if all((_oauth_config(name)['client_id'], _oauth_config(name)['client_secret']))]})


@auth_bp.post('/register')
def register():
    data = request.get_json()
    if data.get('role', 'student') != 'student':
        return error_response('公开注册仅支持学生账号', 40301, None, 403)
    try:
        result = AuthService.register(data.get('username'), data.get('email'), data.get('password'), data.get('real_name'))
        return success_response(result, '注册成功', 0, 201)
    except ValueError as exc:
        return error_response(str(exc), 40001)
    except Exception:
        db.session.rollback()
        current_app.logger.error('Registration failed unexpectedly')
        return error_response('注册服务暂时不可用，请稍后重试', 50001, None, 500)


@auth_bp.post('/login')
def login():
    data = request.get_json()
    try:
        return success_response(AuthService.login(data.get('username'), data.get('password')), '登录成功')
    except ValueError as exc:
        return error_response(str(exc), 40101, None, 401)
    except Exception:
        db.session.rollback()
        return error_response('登录服务暂时不可用，请稍后重试', 50001, None, 500)


@auth_bp.post('/forgot-password')
def forgot_password():
    if not mail_ready():
        return error_response('邮件找回暂未开通，请联系老师或管理员协助', 50301, None, 503)
    try:
        request_reset(request.get_json().get('email'))
        return success_response(None, '如果该邮箱对应可用账号，你将收到重置邮件，请检查收件箱和垃圾邮件')
    except ValueError as exc:
        return error_response(str(exc), 40001)


@auth_bp.post('/reset-password')
def reset_password():
    data = request.get_json()
    try:
        finish_reset(data.get('token'), data.get('password'))
        return success_response(None, '密码已更新，请重新登录')
    except ValueError as exc:
        return error_response(str(exc), 40001)


@auth_bp.post('/logout')
@jwt_required()
def logout():
    data = request.get_json(silent=True)
    if data is not None and not isinstance(data, dict):
        return error_response('请提交有效的 JSON 对象', 40001)
    payload = get_jwt()
    revoke_session(payload)
    # Older clients did not have a shared session id; revoke their refresh too.
    raw = (data or {}).get('refresh_token')
    if isinstance(raw, str):
        try:
            refresh = decode_token(raw)
            if refresh['sub'] == payload['sub'] and refresh['type'] == 'refresh':
                revoke_session(refresh)
        except Exception:
            pass
    db.session.commit()
    return success_response(None, '退出成功')


@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh():
    payload = get_jwt()
    user = db.session.get(User, int(get_jwt_identity()))
    claims = {'username': user.username, 'role': user.role.name, 'auth_version': session_version(user.id)}
    # Keep one family across refresh so logout revokes all access tokens in it.
    claims['sid'] = payload.get('sid') or payload['jti']
    return success_response({'access_token': create_access_token(identity=str(user.id), additional_claims=claims),
        'expiresIn': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())}, '刷新成功')
