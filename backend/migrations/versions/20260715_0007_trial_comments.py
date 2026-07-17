"""trial question comments

Revision ID: 20260715_0007
Revises: 20260628_0006
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = '20260715_0007'
down_revision = '20260628_0006'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if 'trial_comments' not in tables:
        op.create_table(
            'trial_comments',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('question_ref', sa.String(64), nullable=False),
            sa.Column('parent_id', sa.Integer(), sa.ForeignKey('trial_comments.id', ondelete='CASCADE'), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_trial_comments_user_id', 'trial_comments', ['user_id'])
        op.create_index('ix_trial_comments_question_ref', 'trial_comments', ['question_ref'])
        op.create_index('ix_trial_comments_parent_id', 'trial_comments', ['parent_id'])

    if 'trial_comment_likes' not in tables:
        op.create_table(
            'trial_comment_likes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('comment_id', sa.Integer(), sa.ForeignKey('trial_comments.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('comment_id', 'user_id', name='uq_trial_comment_like'),
        )
        op.create_index('ix_trial_comment_likes_comment_id', 'trial_comment_likes', ['comment_id'])
        op.create_index('ix_trial_comment_likes_user_id', 'trial_comment_likes', ['user_id'])


def downgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'trial_comment_likes' in tables:
        op.drop_table('trial_comment_likes')
    if 'trial_comments' in tables:
        op.drop_table('trial_comments')
