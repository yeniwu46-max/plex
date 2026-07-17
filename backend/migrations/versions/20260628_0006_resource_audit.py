"""Add audit_report to resource_generation_tasks.

Revision ID: 20260628_0006
Revises: 20260627_0005
Create Date: 2026-06-28
"""
from alembic import op
import sqlalchemy as sa

revision = '20260628_0006'
down_revision = '20260627_0005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'resource_generation_tasks',
        sa.Column('audit_report', sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column('resource_generation_tasks', 'audit_report')
