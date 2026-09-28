"""Unauthenticated payment-provider callbacks; only signed Alipay notices are accepted."""
from flask import Blueprint, Response, request

from app.services.alipay_payment import AlipayPaymentService


store_payments_bp = Blueprint('store_payments', __name__, url_prefix='/api/v1/payments')


@store_payments_bp.route('/alipay/notify', methods=['POST'])
def alipay_notify():
    params = request.form.to_dict(flat=True)
    try:
        accepted = AlipayPaymentService.apply_notification(params)
    except Exception:
        accepted = False
    return Response('success' if accepted else 'failure', status=200, mimetype='text/plain')
