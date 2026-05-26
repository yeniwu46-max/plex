"""JWT相关工具函数"""
from flask_jwt_extended import create_access_token, create_refresh_token
from datetime import timedelta


def create_tokens(identity, additional_claims=None):
    """
    创建访问和刷新Token

    Args:
        identity: 用户ID或用户对象
        additional_claims: 额外的claim字段（如role、permissions等）

    Returns:
        dict: 包含access_token和refresh_token
    """
    if additional_claims is None:
        additional_claims = {}

    access_token = create_access_token(
        identity=str(identity),
        additional_claims=additional_claims
    )

    refresh_token = create_refresh_token(
        identity=str(identity),
        additional_claims=additional_claims
    )

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
    }


def get_identity_from_token():
    """
    从当前请求的Token中获取身份信息
    需要先运行 verify_jwt_in_request()

    Returns:
        用户身份信息
    """
    from flask_jwt_extended import get_jwt_identity
    return get_jwt_identity()


def get_claims_from_token():
    """
    从当前请求的Token中获取额外claim信息
    需要先运行 verify_jwt_in_request()

    Returns:
        JWT payload中的额外claims
    """
    from flask_jwt_extended import get_jwt
    return get_jwt()
