"""Student catalog and mock entitlement routes (no real payment processing)."""
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.student_store import StudentStoreService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response


student_store_bp = Blueprint('student_store', __name__, url_prefix='/api/v1/student')


@student_store_bp.route('/store/catalog', methods=['GET'])
@jwt_required()
@role_required('student')
def get_store_catalog():
    try:
        return success_response(StudentStoreService.catalog(int(get_jwt_identity())))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_store_bp.route('/entitlements/me', methods=['GET'])
@jwt_required()
@role_required('student')
def get_my_entitlements():
    try:
        return success_response(StudentStoreService.entitlements(int(get_jwt_identity())))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_store_bp.route('/store/history', methods=['GET'])
@jwt_required()
@role_required('student')
def get_store_history():
    try:
        return success_response(StudentStoreService.history(int(get_jwt_identity())))
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_store_bp.route('/store/mock-activation', methods=['POST'])
@jwt_required()
@role_required('student')
def mock_activate_product():
    try:
        payload = request.get_json(silent=True) or {}
        product_code = payload.get('product_code')
        if not isinstance(product_code, str) or not product_code.strip():
            return error_response('缺少商品编号', 40001, None, 400)
        result = StudentStoreService.mock_activate(int(get_jwt_identity()), product_code.strip())
        return success_response(result, '模拟权益已开通；此操作没有扣款', 0, 201)
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40001, None, 400)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)


@student_store_bp.route('/store/challenge-packs/<product_code>', methods=['GET'])
@jwt_required()
@role_required('student')
def get_challenge_pack(product_code):
    try:
        return success_response(
            StudentStoreService.challenge_pack(int(get_jwt_identity()), product_code)
        )
    except PermissionError as exc:
        return error_response(str(exc), 40301, None, 403)
    except ValueError as exc:
        return error_response(str(exc), 40401, None, 404)
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
