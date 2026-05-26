"""认证路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import AuthService
from app.utils.response import success_response, error_response

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


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
