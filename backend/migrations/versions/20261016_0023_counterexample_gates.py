"""Immutable counterexample specifications/versions and validation records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20261016_0023'
down_revision = '20261016_0022'
branch_labels = None
depends_on = None


def upgrade():
    timestamp = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'counterexample_specs' not in tables:
        op.create_table('counterexample_specs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id'), nullable=False),
            sa.Column('content', sa.JSON(), nullable=False), sa.Column('content_hash', sa.String(64), nullable=False),
            sa.Column('approved_at', timestamp, nullable=False))
        op.create_index('ix_counterexample_specs_teacher_id', 'counterexample_specs', ['teacher_id'])
        op.create_index('ix_counterexample_specs_class_id', 'counterexample_specs', ['class_id'])
    if 'counterexample_challenges' not in tables:
        op.create_table('counterexample_challenges',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id'), nullable=False),
            sa.Column('current_revision', sa.Integer(), nullable=False), sa.Column('published_revision', sa.Integer()),
            sa.Column('created_at', timestamp, nullable=False))
        op.create_index('ix_counterexample_challenges_teacher_id', 'counterexample_challenges', ['teacher_id'])
        op.create_index('ix_counterexample_challenges_class_id', 'counterexample_challenges', ['class_id'])
    if 'counterexample_versions' not in tables:
        op.create_table('counterexample_versions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('challenge_id', sa.String(36), sa.ForeignKey('counterexample_challenges.id'), nullable=False),
            sa.Column('revision', sa.Integer(), nullable=False),
            sa.Column('spec_id', sa.String(36), sa.ForeignKey('counterexample_specs.id'), nullable=False),
            sa.Column('candidate', sa.JSON(), nullable=False), sa.Column('manifest_hash', sa.String(64), nullable=False),
            sa.Column('origin', sa.String(30), nullable=False), sa.Column('latest_report_id', sa.String(36)),
            sa.Column('reviewed_report_id', sa.String(36)),
            sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id')), sa.Column('review_note', sa.Text()),
            sa.Column('reviewed_at', timestamp), sa.Column('created_at', timestamp, nullable=False),
            sa.UniqueConstraint('challenge_id', 'revision', name='uq_counterexample_revision'))
        op.create_index('ix_counterexample_versions_challenge_id', 'counterexample_versions', ['challenge_id'])
    if 'counterexample_validations' not in tables:
        op.create_table('counterexample_validations',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('version_id', sa.String(36), sa.ForeignKey('counterexample_versions.id'), nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('manifest_hash', sa.String(64), nullable=False), sa.Column('status', sa.String(20), nullable=False),
            sa.Column('lease_token', sa.String(36), nullable=False), sa.Column('lease_until', timestamp, nullable=False),
            sa.Column('report', sa.JSON()), sa.Column('created_at', timestamp, nullable=False), sa.Column('completed_at', timestamp))
        op.create_index('ix_counterexample_validations_version_id', 'counterexample_validations', ['version_id'])


def downgrade():
    for table in ('counterexample_validations', 'counterexample_versions', 'counterexample_challenges', 'counterexample_specs'):
        op.drop_table(table)
