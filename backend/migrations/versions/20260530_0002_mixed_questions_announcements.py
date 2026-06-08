"""mixed trial questions and system announcements

Revision ID: 20260530_0002
Revises: 20260529_0001
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260530_0002'
down_revision = '20260529_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'system_announcements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('target_role', sa.String(length=20), nullable=False, server_default='teacher'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    with op.batch_alter_table('trials', schema=None) as batch_op:
        batch_op.add_column(sa.Column('draft_questions_json', sa.Text(), nullable=True))

    with op.batch_alter_table('trial_questions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('question_type', sa.String(length=16), nullable=False, server_default='mcq')
        )
        batch_op.add_column(sa.Column('coding_meta_json', sa.Text(), nullable=True))

    with op.batch_alter_table('trial_question_progress', schema=None) as batch_op:
        batch_op.add_column(sa.Column('submitted_code', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('code_passed', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('code_results_json', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('trial_question_progress', schema=None) as batch_op:
        batch_op.drop_column('code_results_json')
        batch_op.drop_column('code_passed')
        batch_op.drop_column('submitted_code')

    with op.batch_alter_table('trial_questions', schema=None) as batch_op:
        batch_op.drop_column('coding_meta_json')
        batch_op.drop_column('question_type')

    with op.batch_alter_table('trials', schema=None) as batch_op:
        batch_op.drop_column('draft_questions_json')

    op.drop_table('system_announcements')
