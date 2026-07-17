"""class join code and enrollment requests

Revision ID: 20260627_0005
Revises: 20260609_0004
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa

revision = '20260627_0005'
down_revision = '20260609_0004'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if 'classes' in tables:
        class_columns = {item['name'] for item in inspector.get_columns('classes')}
        class_indexes = {item['name'] for item in inspector.get_indexes('classes')}
        if 'join_code' not in class_columns:
            with op.batch_alter_table('classes') as batch_op:
                batch_op.add_column(sa.Column('join_code', sa.String(8), nullable=True))
        if 'ix_classes_join_code' not in class_indexes:
            op.create_index('ix_classes_join_code', 'classes', ['join_code'], unique=True)

    if 'class_enrollment_requests' not in tables:
        op.create_table(
            'class_enrollment_requests',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('student_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id'), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('message', sa.Text()),
            sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('review_note', sa.Text()),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('reviewed_at', sa.DateTime()),
        )
        op.create_index('ix_class_enrollment_requests_student_id', 'class_enrollment_requests', ['student_id'])
        op.create_index('ix_class_enrollment_requests_class_id', 'class_enrollment_requests', ['class_id'])


def downgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'class_enrollment_requests' in tables:
        op.drop_table('class_enrollment_requests')
    if 'classes' in tables:
        class_columns = {item['name'] for item in inspector.get_columns('classes')}
        class_indexes = {item['name'] for item in inspector.get_indexes('classes')}
        if 'ix_classes_join_code' in class_indexes:
            op.drop_index('ix_classes_join_code', table_name='classes')
        if 'join_code' in class_columns:
            with op.batch_alter_table('classes') as batch_op:
                batch_op.drop_column('join_code')
