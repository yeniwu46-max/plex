"""baseline schema note

Revision ID: 20260529_0001
Revises:
Create Date: 2026-05-29

生产环境请使用 `flask db upgrade` 或 `alembic upgrade head`；
本地开发仍可通过 `db.create_all()` 建表。本修订记录 learning_resources 等增量表。
"""
from alembic import op
import sqlalchemy as sa

revision = '20260529_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'learning_resources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('knowledge_key', sa.String(length=32), nullable=False),
        sa.Column('resource_type', sa.String(length=24), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content_ref', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_learning_resources_knowledge_key', 'learning_resources', ['knowledge_key'])


def downgrade():
    op.drop_index('ix_learning_resources_knowledge_key', table_name='learning_resources')
    op.drop_table('learning_resources')
