"""Durable, owned candidate generation with fenced stage checkpoints."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20261016_0025'
down_revision = '20261016_0024'
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    timestamp = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')
    if 'counterexample_generation_tasks' not in tables:
        op.create_table('counterexample_generation_tasks',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id'), nullable=False),
            sa.Column('spec_id', sa.String(36), sa.ForeignKey('counterexample_specs.id'), nullable=False),
            sa.Column('spec_hash', sa.String(64), nullable=False),
            sa.Column('bug_kind', sa.String(30), nullable=False),
            sa.Column('challenge_id', sa.String(36), nullable=False, unique=True),
            sa.Column('version_id', sa.String(36), sa.ForeignKey('counterexample_versions.id'), unique=True),
            sa.Column('validation_id', sa.String(36), nullable=False),
            sa.Column('status', sa.String(20), nullable=False), sa.Column('stage', sa.String(20), nullable=False),
            sa.Column('attempts', sa.Integer(), nullable=False), sa.Column('lease_token', sa.String(36)),
            sa.Column('lease_until', timestamp), sa.Column('error_code', sa.String(60)),
            sa.Column('generation_audit', sa.JSON()), sa.Column('pedagogy_review', sa.JSON()),
            sa.Column('created_at', timestamp, nullable=False), sa.Column('completed_at', timestamp))
        op.create_index('ix_counterexample_generation_owner', 'counterexample_generation_tasks', ['teacher_id', 'created_at'])
        op.create_index('ix_counterexample_generation_queue', 'counterexample_generation_tasks', ['status', 'lease_until'])
    if 'counterexample_generation_calls' not in tables:
        op.create_table('counterexample_generation_calls',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('task_id', sa.String(36), sa.ForeignKey('counterexample_generation_tasks.id'), nullable=False),
            sa.Column('attempt', sa.Integer(), nullable=False), sa.Column('stage', sa.String(20), nullable=False),
            sa.Column('audit', sa.JSON()), sa.Column('created_at', timestamp, nullable=False), sa.Column('completed_at', timestamp))
        op.create_index('ix_counterexample_generation_calls_task_id', 'counterexample_generation_calls', ['task_id'])


def downgrade():
    op.drop_table('counterexample_generation_calls')
    op.drop_table('counterexample_generation_tasks')
