"""Track provider payment orders independently from entitlements.

Revision ID: 20260928_0015
Revises: 20260928_0014
Create Date: 2026-09-28
"""
from alembic import op
import sqlalchemy as sa


revision = '20260928_0015'
down_revision = '20260928_0014'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'store_orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_no', sa.String(40), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('store_products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('product_name', sa.String(120), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False, server_default='alipay'),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('provider_trade_no', sa.String(64)),
        sa.Column('qr_code', sa.Text()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('order_no', name='uq_store_orders_order_no'),
        sa.UniqueConstraint('provider_trade_no', name='uq_store_orders_provider_trade_no'),
    )
    op.create_index('ix_store_orders_user_id', 'store_orders', ['user_id'])
    op.create_index('ix_store_orders_product_id', 'store_orders', ['product_id'])
    op.create_index('ix_store_orders_status', 'store_orders', ['status'])
    op.create_index('ix_store_orders_expires_at', 'store_orders', ['expires_at'])
    op.create_index('ix_store_orders_paid_at', 'store_orders', ['paid_at'])
    op.create_index('ix_store_orders_created_at', 'store_orders', ['created_at'])


def downgrade():
    op.drop_table('store_orders')
