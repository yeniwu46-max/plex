"""Student store products and mock entitlement history.

Revision ID: 20260928_0013
Revises: 20260924_0012
Create Date: 2026-09-28
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = '20260928_0013'
down_revision = '20260924_0012'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'store_products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(64), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('product_type', sa.String(24), nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('duration_days', sa.Integer()),
        sa.Column('benefits_json', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_store_products_code', 'store_products', ['code'], unique=True)
    op.create_index('ix_store_products_product_type', 'store_products', ['product_type'])
    op.create_index('ix_store_products_is_active', 'store_products', ['is_active'])

    op.create_table(
        'store_product_problems',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('store_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', sa.Integer(), sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('product_id', 'problem_id', name='uq_store_product_problem'),
    )
    op.create_index('ix_store_product_problems_product_id', 'store_product_problems', ['product_id'])
    op.create_index('ix_store_product_problems_problem_id', 'store_product_problems', ['problem_id'])

    op.create_table(
        'user_entitlements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('store_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(16), nullable=False, server_default='mock'),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_user_entitlements_user_id', 'user_entitlements', ['user_id'])
    op.create_index('ix_user_entitlements_product_id', 'user_entitlements', ['product_id'])
    op.create_index('ix_user_entitlements_starts_at', 'user_entitlements', ['starts_at'])
    op.create_index('ix_user_entitlements_expires_at', 'user_entitlements', ['expires_at'])
    op.create_index('ix_user_entitlements_created_at', 'user_entitlements', ['created_at'])

    products = sa.table(
        'store_products',
        sa.column('id', sa.Integer()), sa.column('code', sa.String()),
        sa.column('name', sa.String()), sa.column('description', sa.Text()),
        sa.column('product_type', sa.String()), sa.column('price_cents', sa.Integer()),
        sa.column('duration_days', sa.Integer()), sa.column('benefits_json', sa.JSON()),
        sa.column('is_active', sa.Boolean()), sa.column('sort_order', sa.Integer()),
        sa.column('created_at', sa.DateTime()), sa.column('updated_at', sa.DateTime()),
    )
    now = datetime.utcnow()
    op.bulk_insert(products, [
        {'id': 1, 'code': 'explorer_monthly', 'name': '探索月卡', 'description': '30 天会员权益：当前主题挑战包与进阶阶段报告。', 'product_type': 'membership', 'price_cents': 990, 'duration_days': 30, 'benefits_json': ['member_challenge_pack', 'phase_report'], 'is_active': True, 'sort_order': 10, 'created_at': now, 'updated_at': now},
        {'id': 2, 'code': 'explorer_annual', 'name': '探索年卡', 'description': '365 天会员权益：当前主题挑战包与进阶阶段报告。', 'product_type': 'membership', 'price_cents': 6800, 'duration_days': 365, 'benefits_json': ['member_challenge_pack', 'phase_report'], 'is_active': True, 'sort_order': 20, 'created_at': now, 'updated_at': now},
        {'id': 3, 'code': 'challenge_pack_algorithms_01', 'name': '算法基础 · 星轨挑战包', 'description': '10 道精选编程题组成的额外挑战，不影响免费学习主线。', 'product_type': 'challenge_pack', 'price_cents': 600, 'duration_days': None, 'benefits_json': ['challenge_pack_algorithms_01'], 'is_active': True, 'sort_order': 30, 'created_at': now, 'updated_at': now},
    ])

    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if 'problems' in tables:
        problem_columns = {col['name'] for col in sa.inspect(bind).get_columns('problems')}
        required = {'id', 'is_active', 'question_type', 'needs_review', 'star_difficulty', 'problem_no'}
        if required.issubset(problem_columns):
            problem_table = sa.table(
                'problems', sa.column('id', sa.Integer()), sa.column('is_active', sa.Boolean()),
                sa.column('question_type', sa.String()), sa.column('needs_review', sa.Boolean()),
                sa.column('star_difficulty', sa.Integer()), sa.column('problem_no', sa.String()),
            )
            ids = bind.execute(
                sa.select(problem_table.c.id)
                .where(
                    problem_table.c.is_active.is_(True),
                    problem_table.c.question_type == 'coding',
                    sa.or_(problem_table.c.needs_review.is_(False), problem_table.c.needs_review.is_(None)),
                )
                .order_by(problem_table.c.star_difficulty, problem_table.c.problem_no)
                .limit(10)
            ).scalars().all()
            if ids:
                links = sa.table(
                    'store_product_problems', sa.column('product_id', sa.Integer()),
                    sa.column('problem_id', sa.Integer()), sa.column('sort_order', sa.Integer()),
                )
                op.bulk_insert(links, [
                    {'product_id': 3, 'problem_id': problem_id, 'sort_order': index}
                    for index, problem_id in enumerate(ids)
                ])


def downgrade():
    op.drop_table('user_entitlements')
    op.drop_table('store_product_problems')
    op.drop_table('store_products')
