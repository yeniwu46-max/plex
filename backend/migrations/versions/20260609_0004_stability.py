"""stability fields and profile suggestions

Revision ID: 20260609_0004
Revises: 20260609_0003
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = '20260609_0004'
down_revision = '20260609_0003'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    task_columns = {item['name'] for item in inspector.get_columns('resource_generation_tasks')}
    task_indexes = {item['name'] for item in inspector.get_indexes('resource_generation_tasks')}
    with op.batch_alter_table('resource_generation_tasks') as batch_op:
        if 'profile_version' not in task_columns:
            batch_op.add_column(sa.Column('profile_version', sa.Integer(), nullable=False, server_default='0'))
        if 'request_fingerprint' not in task_columns:
            batch_op.add_column(sa.Column('request_fingerprint', sa.String(64), nullable=False, server_default=''))
        if 'idempotency_key' not in task_columns:
            batch_op.add_column(sa.Column('idempotency_key', sa.String(100)))
        if 'recoverable' not in task_columns:
            batch_op.add_column(sa.Column('recoverable', sa.Boolean(), nullable=False, server_default=sa.true()))
        if 'ix_resource_generation_tasks_request_fingerprint' not in task_indexes:
            batch_op.create_index('ix_resource_generation_tasks_request_fingerprint', ['request_fingerprint'])
        if 'ix_resource_generation_tasks_idempotency_key' not in task_indexes:
            batch_op.create_index('ix_resource_generation_tasks_idempotency_key', ['idempotency_key'])

    resource_columns = {item['name'] for item in inspector.get_columns('personalized_learning_resources')}
    if 'risk_reasons' not in resource_columns:
        with op.batch_alter_table('personalized_learning_resources') as batch_op:
            batch_op.add_column(sa.Column('risk_reasons', sa.JSON(), nullable=True))
        op.execute("UPDATE personalized_learning_resources SET risk_reasons = '[]' WHERE risk_reasons IS NULL")
        with op.batch_alter_table('personalized_learning_resources') as batch_op:
            batch_op.alter_column('risk_reasons', existing_type=sa.JSON(), nullable=False)

    if 'student_profile_suggestions' not in tables:
        op.create_table(
            'student_profile_suggestions',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('dimension', sa.String(64), nullable=False),
            sa.Column('proposed_value', sa.String(500), nullable=False),
            sa.Column('evidence', sa.JSON(), nullable=False),
            sa.Column('source', sa.String(32), nullable=False),
            sa.Column('status', sa.String(16), nullable=False),
            sa.Column('profile_version', sa.Integer(), nullable=False),
            sa.Column('resolved_at', sa.DateTime()),
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_student_profile_suggestions_user_id', 'student_profile_suggestions', ['user_id'])
        op.create_index('ix_student_profile_suggestions_dimension', 'student_profile_suggestions', ['dimension'])
        op.create_index('ix_student_profile_suggestions_status', 'student_profile_suggestions', ['status'])


def downgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'student_profile_suggestions' in tables:
        op.drop_table('student_profile_suggestions')
    resource_columns = {item['name'] for item in inspector.get_columns('personalized_learning_resources')}
    if 'risk_reasons' in resource_columns:
        with op.batch_alter_table('personalized_learning_resources') as batch_op:
            batch_op.drop_column('risk_reasons')
    task_columns = {item['name'] for item in inspector.get_columns('resource_generation_tasks')}
    task_indexes = {item['name'] for item in inspector.get_indexes('resource_generation_tasks')}
    with op.batch_alter_table('resource_generation_tasks') as batch_op:
        if 'ix_resource_generation_tasks_idempotency_key' in task_indexes:
            batch_op.drop_index('ix_resource_generation_tasks_idempotency_key')
        if 'ix_resource_generation_tasks_request_fingerprint' in task_indexes:
            batch_op.drop_index('ix_resource_generation_tasks_request_fingerprint')
        for column in ('recoverable', 'idempotency_key', 'request_fingerprint', 'profile_version'):
            if column in task_columns:
                batch_op.drop_column(column)
