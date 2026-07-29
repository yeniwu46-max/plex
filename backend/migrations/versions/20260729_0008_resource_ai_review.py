"""Add AI review anomaly fields to personalized resources.

Revision ID: 20260729_0008
Revises: 20260715_0007
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa


revision = '20260729_0008'
down_revision = '20260715_0007'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'personalized_learning_resources' not in tables:
        return
    columns = {col['name'] for col in inspector.get_columns('personalized_learning_resources')}
    if 'is_anomaly' not in columns:
        op.add_column(
            'personalized_learning_resources',
            sa.Column('is_anomaly', sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if 'student_warning' not in columns:
        op.add_column(
            'personalized_learning_resources',
            sa.Column('student_warning', sa.String(500), nullable=True),
        )
    if 'ai_review' not in columns:
        op.add_column(
            'personalized_learning_resources',
            sa.Column('ai_review', sa.JSON(), nullable=True),
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'personalized_learning_resources' not in tables:
        return
    columns = {col['name'] for col in inspector.get_columns('personalized_learning_resources')}
    if 'ai_review' in columns:
        op.drop_column('personalized_learning_resources', 'ai_review')
    if 'student_warning' in columns:
        op.drop_column('personalized_learning_resources', 'student_warning')
    if 'is_anomaly' in columns:
        op.drop_column('personalized_learning_resources', 'is_anomaly')
