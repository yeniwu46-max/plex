"""Persist challenge-pack completions and describe the expanded benefits.

Revision ID: 20260928_0014
Revises: 20260928_0013
Create Date: 2026-09-28
"""
from alembic import op
import sqlalchemy as sa


revision = '20260928_0014'
down_revision = '20260928_0013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_challenge_progress',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('store_products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', sa.Integer(), sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'product_id', 'problem_id', name='uq_user_challenge_progress'),
    )
    op.create_index('ix_user_challenge_progress_user_id', 'user_challenge_progress', ['user_id'])
    op.create_index('ix_user_challenge_progress_product_id', 'user_challenge_progress', ['product_id'])
    op.create_index('ix_user_challenge_progress_problem_id', 'user_challenge_progress', ['problem_id'])

    products = sa.table(
        'store_products',
        sa.column('code', sa.String(64)),
        sa.column('benefits_json', sa.JSON()),
        sa.column('description', sa.Text()),
    )
    connection = op.get_bind()
    connection.execute(
        products.update().where(products.c.code == 'explorer_monthly').values(
        description='30 天会员：当前星际挑战包、进阶阶段报告与挑战进度云端存档。',
            benefits_json=[
                '算法基础星际挑战包访问权',
                '进阶阶段学习报告',
                '挑战通关进度跨设备保存',
                '会员有效期内可体验当前主题挑战包',
            ],
        )
    )
    connection.execute(
        products.update().where(products.c.code == 'explorer_annual').values(
            description='365 天会员：当前星际挑战包、进阶阶段报告与挑战进度云端存档。',
            benefits_json=[
                '算法基础星际挑战包访问权',
                '进阶阶段学习报告',
                '挑战通关进度跨设备保存',
                '会员有效期内可体验当前主题挑战包',
            ],
        )
    )
    connection.execute(
        products.update().where(products.c.code == 'challenge_pack_algorithms_01').values(
            description='十道由基础指令逐步进阶到算法实战的星际任务，不影响免费学习主线。',
            benefits_json=[
                '10 道算法基础编程任务',
                '星际任务简报与分关挑战路线',
                '挑战通关进度跨设备保存',
                '永久保留该挑战包访问权',
            ],
        )
    )

    # 固定首发挑战内容：从已有题库挑选一条逐步进阶的真实练习路线。
    # 若某环境缺少其中任一道题，则保留 0013 迁移选出的可用题目，服务层会补足题数。
    bind = op.get_bind()
    table_names = set(sa.inspect(bind).get_table_names())
    if {'problems', 'store_product_problems'}.issubset(table_names):
        problem_columns = {col['name'] for col in sa.inspect(bind).get_columns('problems')}
        if {'id', 'problem_no', 'is_active', 'question_type', 'needs_review'}.issubset(problem_columns):
            problems = sa.table(
                'problems',
                sa.column('id', sa.Integer()),
                sa.column('problem_no', sa.String(8)),
                sa.column('is_active', sa.Boolean()),
                sa.column('question_type', sa.String(16)),
                sa.column('needs_review', sa.Boolean()),
            )
            # Product id is read separately to keep the existing links portable across seeded IDs.
            product_table = sa.table(
                'store_products', sa.column('id', sa.Integer()), sa.column('code', sa.String(64)),
            )
            product = bind.execute(sa.select(product_table.c.id).where(
                product_table.c.code == 'challenge_pack_algorithms_01',
            )).first()
            if product:
                preferred_codes = (
                    'A001', 'B003', 'BR002', 'D009', 'D015',
                    'AR001', 'FN002', 'LP001', 'SE003', 'SE005',
                )
                rows = bind.execute(
                    sa.select(problems.c.id, problems.c.problem_no).where(
                        problems.c.problem_no.in_(preferred_codes),
                        problems.c.is_active.is_(True),
                        problems.c.question_type == 'coding',
                        sa.or_(problems.c.needs_review.is_(False), problems.c.needs_review.is_(None)),
                    )
                ).all()
                by_code = {row.problem_no: row.id for row in rows}
                if all(code in by_code for code in preferred_codes):
                    links = sa.table(
                        'store_product_problems',
                        sa.column('product_id', sa.Integer()),
                        sa.column('problem_id', sa.Integer()),
                        sa.column('sort_order', sa.Integer()),
                    )
                    bind.execute(links.delete().where(links.c.product_id == product.id))
                    op.bulk_insert(links, [
                        {'product_id': product.id, 'problem_id': by_code[code], 'sort_order': index}
                        for index, code in enumerate(preferred_codes)
                    ])


def downgrade():
    op.drop_table('user_challenge_progress')
