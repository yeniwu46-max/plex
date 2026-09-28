"""Alipay face-to-face QR order creation and trusted payment notification handling."""
import base64
import json
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
from zoneinfo import ZoneInfo

import qrcode
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from flask import current_app
from app.models import StoreOrder, StoreProduct, User, UserEntitlement, db
from app.services.student_store import MEMBERSHIP_CODES, StudentStoreService
from app.utils.time import utc_now


class PaymentUnavailableError(RuntimeError):
    pass


class PaymentProviderError(RuntimeError):
    pass


class AlipayPaymentService:
    SUCCESS_STATUSES = {'TRADE_SUCCESS', 'TRADE_FINISHED'}

    @classmethod
    def configured(cls) -> bool:
        cfg = current_app.config
        return bool(
            cfg.get('ALIPAY_PAYMENT_ENABLED', False)
            and cls.credentials_ready()
        )

    @staticmethod
    def credentials_ready() -> bool:
        cfg = current_app.config
        return bool(
            cfg.get('ALIPAY_APP_ID')
            and cfg.get('ALIPAY_PRIVATE_KEY')
            and cfg.get('ALIPAY_PUBLIC_KEY')
            and cfg.get('ALIPAY_SELLER_ID')
            and str(cfg.get('ALIPAY_NOTIFY_URL', '')).startswith('https://')
            and str(cfg.get('ALIPAY_GATEWAY', '')).startswith('https://')
        )

    @staticmethod
    def notification_verification_ready() -> bool:
        cfg = current_app.config
        return bool(cfg.get('ALIPAY_APP_ID') and cfg.get('ALIPAY_PUBLIC_KEY') and cfg.get('ALIPAY_SELLER_ID'))

    @staticmethod
    def _key_text(raw: str, kind: str) -> str:
        value = raw.strip().replace('\\n', '\n')
        if '-----BEGIN ' in value:
            return value
        if kind == 'private':
            return f'-----BEGIN PRIVATE KEY-----\n{value}\n-----END PRIVATE KEY-----'
        return f'-----BEGIN PUBLIC KEY-----\n{value}\n-----END PUBLIC KEY-----'

    @classmethod
    def _private_key(cls):
        raw = cls._key_text(current_app.config['ALIPAY_PRIVATE_KEY'], 'private').encode('utf-8')
        try:
            return serialization.load_pem_private_key(raw, password=None)
        except ValueError:
            # Alipay's older key format is PKCS#1 rather than PKCS#8.
            wrapped = cls._key_text(current_app.config['ALIPAY_PRIVATE_KEY'], 'private')
            if wrapped.startswith('-----BEGIN PRIVATE KEY-----'):
                wrapped = wrapped.replace('BEGIN PRIVATE KEY', 'BEGIN RSA PRIVATE KEY').replace(
                    'END PRIVATE KEY', 'END RSA PRIVATE KEY',
                )
            return serialization.load_pem_private_key(wrapped.encode('utf-8'), password=None)

    @classmethod
    def _public_key(cls):
        return serialization.load_pem_public_key(
            cls._key_text(current_app.config['ALIPAY_PUBLIC_KEY'], 'public').encode('utf-8'),
        )

    @staticmethod
    def _signing_content(params: dict) -> bytes:
        pairs = [
            (str(key), str(value))
            for key, value in params.items()
            if key not in {'sign', 'sign_type'} and value is not None and str(value) != ''
        ]
        return '&'.join(f'{key}={value}' for key, value in sorted(pairs)).encode('utf-8')

    @classmethod
    def _sign(cls, params: dict) -> str:
        signature = cls._private_key().sign(
            cls._signing_content(params), padding.PKCS1v15(), hashes.SHA256(),
        )
        return base64.b64encode(signature).decode('ascii')

    @classmethod
    def verify_notification(cls, params: dict) -> bool:
        signature = params.get('sign')
        if not signature or params.get('sign_type') != 'RSA2':
            return False
        try:
            cls._public_key().verify(
                base64.b64decode(signature, validate=True),
                cls._signing_content(params),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    @classmethod
    def _verify_api_response(cls, payload: dict, result_node: dict) -> bool:
        signature = payload.get('sign')
        if not signature:
            return False
        # Alipay signs the inner JSON response object, including braces.
        content = json.dumps(
            result_node, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
        ).replace('/', '\\/').encode('utf-8')
        try:
            cls._public_key().verify(
                base64.b64decode(signature, validate=True),
                content,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _amount_text(cents: int) -> str:
        return f'{Decimal(cents) / Decimal(100):.2f}'

    @staticmethod
    def _qr_data_url(value: str) -> str:
        image = qrcode.make(value)
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')

    @classmethod
    def create_order(cls, user_id: int, product_code: str) -> dict:
        if not cls.configured():
            raise PaymentUnavailableError('支付宝商户支付尚未配置')
        StudentStoreService.ensure_catalog()
        product = StoreProduct.query.filter_by(code=product_code, is_active=True).first()
        if not product:
            raise ValueError('商品不存在或暂未开放')
        if product.product_type == 'challenge_pack' and len(product.challenge_problems) != 10:
            raise ValueError('挑战包正在准备中，暂不可开通')

        now = utc_now()
        timeout_minutes = max(5, min(int(current_app.config.get('ALIPAY_QR_TIMEOUT_MINUTES', 15)), 30))
        StoreOrder.query.filter(
            StoreOrder.user_id == user_id,
            StoreOrder.status == 'pending',
            StoreOrder.expires_at <= now,
        ).update({StoreOrder.status: 'expired'}, synchronize_session=False)
        pending = StoreOrder.query.filter_by(user_id=user_id, status='pending').filter(
            StoreOrder.expires_at > now,
        ).order_by(StoreOrder.created_at.desc()).first()
        if pending:
            if pending.product_id != product.id:
                raise ValueError('你有一笔未完成的支付宝订单，请先完成或等待二维码过期')
            data = pending.to_dict()
            if pending.qr_code:
                data['qr_image_data_url'] = cls._qr_data_url(pending.qr_code)
            return data

        order = StoreOrder(
            order_no=f'PLX{now:%Y%m%d%H%M%S}{secrets.token_hex(6).upper()}',
            user_id=user_id,
            product_id=product.id,
            product_name=product.name,
            amount_cents=product.price_cents,
            provider='alipay',
            status='pending',
            expires_at=now + timedelta(minutes=timeout_minutes),
        )
        db.session.add(order)
        db.session.commit()

        biz_content = {
            'out_trade_no': order.order_no,
            'total_amount': cls._amount_text(order.amount_cents),
            'subject': f'PLEX {product.name}',
            'body': product.description[:128],
            'timeout_express': f'{timeout_minutes}m',
            'qr_code_timeout_express': f'{timeout_minutes}m',
            'seller_id': current_app.config['ALIPAY_SELLER_ID'],
        }
        params = {
            'app_id': current_app.config['ALIPAY_APP_ID'],
            'method': 'alipay.trade.precreate',
            'format': 'JSON',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'notify_url': current_app.config['ALIPAY_NOTIFY_URL'],
            'biz_content': json.dumps(biz_content, ensure_ascii=False, sort_keys=True, separators=(',', ':')),
        }
        try:
            params['sign'] = cls._sign(params)
            response = requests.post(
                current_app.config['ALIPAY_GATEWAY'], data=params,
                timeout=(5, 15), allow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            result = payload.get('alipay_trade_precreate_response') or {}
            if not cls._verify_api_response(payload, result):
                raise PaymentProviderError('支付宝预下单响应验签失败')
            if result.get('code') != '10000' or result.get('out_trade_no') != order.order_no or not result.get('qr_code'):
                raise PaymentProviderError('支付宝未能创建支付二维码')
        except PaymentProviderError:
            order.status = 'failed'
            db.session.commit()
            raise
        except Exception as exc:
            order.status = 'failed'
            db.session.commit()
            raise PaymentProviderError('连接支付宝失败，请稍后重试') from exc

        order.qr_code = result['qr_code']
        db.session.commit()
        data = order.to_dict()
        data['qr_image_data_url'] = cls._qr_data_url(order.qr_code)
        return data

    @classmethod
    def order_status(cls, user_id: int, order_no: str) -> dict:
        order = StoreOrder.query.filter_by(user_id=user_id, order_no=order_no).first()
        if not order:
            raise ValueError('订单不存在')
        if order.status == 'pending' and order.expires_at <= utc_now():
            order.status = 'expired'
            db.session.commit()
        return order.to_dict()

    @classmethod
    def apply_notification(cls, params: dict) -> bool:
        # Keep accepting signed notices for existing open orders even if the
        # operator temporarily disables creation of new payment orders.
        if not cls.notification_verification_ready() or not cls.verify_notification(params):
            return False
        if params.get('app_id') != current_app.config['ALIPAY_APP_ID']:
            return False
        if params.get('seller_id') != current_app.config['ALIPAY_SELLER_ID']:
            return False
        order_no = params.get('out_trade_no')
        if not order_no:
            return False
        try:
            reported_amount = Decimal(params.get('total_amount', '0')) * 100
            if reported_amount != reported_amount.to_integral_value():
                return False
            reported_cents = int(reported_amount)
        except (InvalidOperation, ValueError):
            return False

        order = StoreOrder.query.filter_by(order_no=order_no).with_for_update().first()
        if not order or order.provider != 'alipay' or reported_cents != order.amount_cents:
            return False
        trade_no = params.get('trade_no')
        if not trade_no:
            return False
        if order.status == 'paid':
            return order.provider_trade_no == trade_no
        if params.get('trade_status') not in cls.SUCCESS_STATUSES:
            if params.get('trade_status') == 'TRADE_CLOSED' and order.status == 'pending':
                order.status = 'closed'
                db.session.commit()
            return True

        if order.status not in {'pending', 'expired'}:
            return False
        try:
            paid_at = datetime.strptime(params['gmt_payment'], '%Y-%m-%d %H:%M:%S').replace(
                tzinfo=ZoneInfo('Asia/Shanghai'),
            ).astimezone(timezone.utc).replace(tzinfo=None)
        except (KeyError, TypeError, ValueError):
            paid_at = utc_now()

        product = db.session.get(StoreProduct, order.product_id)
        if not product:
            return False
        order.status = 'paid'
        order.provider_trade_no = trade_no
        order.paid_at = paid_at
        cls._grant_paid_order(order, product, paid_at)
        db.session.commit()
        return True

    @staticmethod
    def _grant_paid_order(order: StoreOrder, product: StoreProduct, paid_at: datetime) -> None:
        if product.product_type == 'challenge_pack':
            existing = UserEntitlement.query.filter_by(
                user_id=order.user_id, product_id=product.id, expires_at=None,
            ).first()
            if not existing:
                db.session.add(UserEntitlement(
                    user_id=order.user_id, product_id=product.id, source='alipay', starts_at=paid_at,
                ))
            return

        current_end = (
            UserEntitlement.query.join(StoreProduct)
            .filter(
                UserEntitlement.user_id == order.user_id,
                StoreProduct.code.in_(MEMBERSHIP_CODES),
                UserEntitlement.expires_at > paid_at,
            )
            .with_for_update()
            .all()
        )
        starts_at = max((grant.expires_at for grant in current_end if grant.expires_at), default=paid_at)
        expires_at = starts_at + timedelta(days=product.duration_days)
        db.session.add(UserEntitlement(
            user_id=order.user_id,
            product_id=product.id,
            source='alipay',
            starts_at=starts_at,
            expires_at=expires_at,
        ))

    @staticmethod
    def admin_orders(limit=200) -> list[dict]:
        rows = StoreOrder.query.order_by(StoreOrder.created_at.desc()).limit(limit).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def admin_entitlements(limit=200) -> list[dict]:
        rows = (
            UserEntitlement.query.join(StoreProduct)
            .order_by(UserEntitlement.created_at.desc())
            .limit(limit)
            .all()
        )
        results = []
        for row in rows:
            user = db.session.get(User, row.user_id)
            results.append({
                **row.to_dict(),
                'user_id': row.user_id,
                'username': user.username if user else None,
                'real_name': user.real_name if user else None,
                'is_active': bool(
                    row.starts_at <= utc_now() and (row.expires_at is None or row.expires_at > utc_now())
                ),
            })
        return results
