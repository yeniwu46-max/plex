"""
统一响应格式工具
"""
from flask import jsonify


def success_response(data=None, message="操作成功", code=0, status_code=200):
    """
    成功响应

    Args:
        data: 返回数据
        message: 消息
        code: 错误码（0为成功）
        status_code: HTTP状态码

    Returns:
        tuple: (JSON响应, HTTP状态码)
    """
    response = {
        "code": code,
        "message": message,
        "data": data
    }
    return jsonify(response), status_code


def error_response(message="操作失败", code=40001, data=None, status_code=400):
    """
    错误响应

    Args:
        message: 错误消息
        code: 错误码
        data: 返回数据
        status_code: HTTP状态码

    Returns:
        tuple: (JSON响应, HTTP状态码)
    """
    response = {
        "code": code,
        "message": message,
        "data": data
    }
    return jsonify(response), status_code


def paginated_response(items, total, page, limit, message="获取成功", code=0, status_code=200):
    """
    分页响应

    Args:
        items: 数据列表
        total: 总数
        page: 当前页
        limit: 每页数量
        message: 消息
        code: 错误码
        status_code: HTTP状态码

    Returns:
        tuple: (JSON响应, HTTP状态码)
    """
    data = {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }
    return success_response(data, message, code, status_code)
