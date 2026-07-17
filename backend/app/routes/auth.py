"""认证路由"""
import json
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, redirect, request, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from itsdangerous import BadSignature, URLSafeSerializer
from app.services import AuthService
from app.utils.response import success_response, error_response

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


def _frontend_oauth_redirect(params):
    base = current_app.config.get('FRONTEND_BASE_URL', 'http://localhost:5180').rstrip('/')
    return redirect(f"{base}/oauth/callback#{urlencode(params)}")


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
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt='oauth-state')


def _provider_profile(provider, access_token):
    headers = {'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
    if provider == 'google':
        resp = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            'id': data.get('sub'),
            'email': data.get('email'),
            'name': data.get('name'),
            'avatar_url': data.get('picture'),
        }

    resp = requests.get('https://api.github.com/user', headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    email = data.get('email')
    if not email:
        emails_resp = requests.get('https://api.github.com/user/emails', headers=headers, timeout=10)
        emails_resp.raise_for_status()
        emails = emails_resp.json()
        primary = next((item for item in emails if item.get('primary') and item.get('verified')), None)
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
        'redirect': request.args.get('redirect') or '/',
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
    return redirect(f"{config['authorize_url']}?{urlencode(params)}")


@auth_bp.route('/oauth/<provider>/callback', methods=['GET'])
def oauth_callback(provider):
    """Handle Google/GitHub OAuth callback and hand the JWT session to Vue."""
    config = _oauth_config(provider)
    if not config:
        return _frontend_oauth_redirect({'error': '暂不支持该第三方登录方式'})

    if request.args.get('error'):
        return _frontend_oauth_redirect({'error': request.args.get('error_description') or request.args['error']})

    try:
        state = _state_serializer().loads(request.args.get('state', ''))
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
        if not profile.get('id'):
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
    except Exception as e:
        current_app.logger.exception('OAuth login failed for %s', provider)
        return _frontend_oauth_redirect({'error': str(e)})


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['username', 'email', 'password', 'real_name']
        for field in required_fields:
            if not data.get(field):
                return error_response(f'缺少必需字段: {field}', 40001)
        
        result = AuthService.register(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            real_name=data['real_name'],
            role=data.get('role', 'student')
        )
        
        return success_response(result, '注册成功', 0, 201)

    except Exception as e:
        return error_response(str(e), 40001)


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return error_response('用户名或密码不能为空', 40001)
        
        result = AuthService.login(
            username=data['username'],
            password=data['password']
        )
        
        return success_response(result, '登录成功')
    
    except Exception as e:
        return error_response(str(e), 40001)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """用户登出"""
    # JWT无状态，这里只返回成功
    return success_response(None, '登出成功')


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """刷新Token"""
    try:
        from flask_jwt_extended import create_access_token
        from flask import current_app
        
        current_user = get_jwt_identity()
        
        access_token = create_access_token(identity=current_user)
        
        return success_response({
            'access_token': access_token,
            'expiresIn': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()),
        }, '刷新成功')
    
    except Exception as e:
        return error_response(str(e), 50001)
