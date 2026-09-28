"""Student store catalog and entitlement grants (mock-only for the first release)."""
from app.utils.time import utc_now
from . import db


class StoreProduct(db.Model):
    __tablename__ = 'store_products'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    product_type = db.Column(db.String(24), nullable=False, index=True)
    price_cents = db.Column(db.Integer, nullable=False)
    duration_days = db.Column(db.Integer)
    benefits_json = db.Column(db.JSON, nullable=False, default=list)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    challenge_problems = db.relationship(
        'StoreProductProblem', backref='product', cascade='all, delete-orphan',
        order_by='StoreProductProblem.sort_order',
    )
    grants = db.relationship('UserEntitlement', backref='product', cascade='all, delete-orphan')

    def to_dict(self, *, owned=False, active=False, expires_at=None, available=True):
        return {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'product_type': self.product_type,
            'price_cents': self.price_cents,
            'duration_days': self.duration_days,
            'benefits': self.benefits_json or [],
            'owned': bool(owned),
            'active': bool(active),
            'expires_at': expires_at.isoformat() + 'Z' if expires_at else None,
            'available': bool(available),
        }


class StoreProductProblem(db.Model):
    __tablename__ = 'store_product_problems'
    __table_args__ = (db.UniqueConstraint('product_id', 'problem_id', name='uq_store_product_problem'),)

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('store_products.id', ondelete='CASCADE'), nullable=False, index=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    problem = db.relationship('Problem')


class UserEntitlement(db.Model):
    """Append-only entitlement history from mock activation or a verified provider payment."""
    __tablename__ = 'user_entitlements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('store_products.id', ondelete='CASCADE'), nullable=False, index=True)
    source = db.Column(db.String(16), nullable=False, default='mock')
    starts_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    expires_at = db.Column(db.DateTime, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'product_code': self.product.code if self.product else None,
            'product_name': self.product.name if self.product else None,
            'source': self.source,
            'starts_at': self.starts_at.isoformat() + 'Z' if self.starts_at else None,
            'expires_at': self.expires_at.isoformat() + 'Z' if self.expires_at else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class StoreOrder(db.Model):
    """Payment order; only a verified provider callback may change it to paid."""
    __tablename__ = 'store_orders'

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(40), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('store_products.id', ondelete='RESTRICT'), nullable=False, index=True)
    product_name = db.Column(db.String(120), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    provider = db.Column(db.String(16), nullable=False, default='alipay')
    status = db.Column(db.String(16), nullable=False, default='pending', index=True)
    provider_trade_no = db.Column(db.String(64), unique=True, index=True)
    qr_code = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    paid_at = db.Column(db.DateTime, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship('User')
    product = db.relationship('StoreProduct')

    def to_dict(self):
        return {
            'order_no': self.order_no,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'real_name': self.user.real_name if self.user else None,
            'product_code': self.product.code if self.product else None,
            'product_name': self.product_name,
            'amount_cents': self.amount_cents,
            'provider': self.provider,
            'status': self.status,
            'provider_trade_no': self.provider_trade_no,
            'expires_at': self.expires_at.isoformat() + 'Z' if self.expires_at else None,
            'paid_at': self.paid_at.isoformat() + 'Z' if self.paid_at else None,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class UserChallengeProgress(db.Model):
    """First-pass completion records for owned challenge-pack missions."""
    __tablename__ = 'user_challenge_progress'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', 'problem_id', name='uq_user_challenge_progress'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('store_products.id', ondelete='CASCADE'), nullable=False, index=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    product = db.relationship('StoreProduct')
    problem = db.relationship('Problem')
