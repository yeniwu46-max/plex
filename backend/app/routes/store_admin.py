"""Administrative view of paid orders and users who received benefits."""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_

from app.models import StoreOrder, UserEntitlement, db
from app.services.alipay_payment import AlipayPaymentService
from app.utils.decorators import role_required
from app.utils.response import error_response, success_response
from app.utils.time import utc_now


store_admin_bp = Blueprint('store_admin', __name__, url_prefix='/api/v1/admin/store')


@store_admin_bp.route('/overview', methods=['GET'])
@jwt_required()
@role_required('admin')
def store_overview():
    try:
        limit = min(max(request.args.get('limit', 200, type=int), 1), 500)
        orders = AlipayPaymentService.admin_orders(limit)
        entitlements = AlipayPaymentService.admin_entitlements(limit)
        return success_response({
            'summary': {
                'paid_orders': StoreOrder.query.filter_by(status='paid').count(),
                'pending_orders': StoreOrder.query.filter_by(status='pending').count(),
                'gross_paid_cents': db.session.query(func.coalesce(func.sum(StoreOrder.amount_cents), 0))
                    .filter(StoreOrder.status == 'paid').scalar(),
                'active_entitlements': UserEntitlement.query.filter(
                    UserEntitlement.starts_at <= utc_now(),
                    or_(UserEntitlement.expires_at.is_(None), UserEntitlement.expires_at > utc_now()),
                ).count(),
            },
            'recent_orders': orders,
            'recent_entitlements': entitlements,
        })
    except Exception as exc:
        return error_response(str(exc), 50001, None, 500)
