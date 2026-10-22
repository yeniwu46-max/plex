"""Owned counterexample attempts and separate practice evidence, never mastery scores."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20261016_0024'
down_revision = '20261016_0023'
branch_labels = None
depends_on = None


def upgrade():
    timestamp = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'blocked_reason' not in {c['name'] for c in inspector.get_columns('counterexample_versions')}:
        op.add_column('counterexample_versions', sa.Column('blocked_reason', sa.String(80)))
    columns = {c['name'] for c in inspector.get_columns('learner_concept_states')}
    for name in ('counterexample_count', 'counterexample_success'):
        if name not in columns:
            op.add_column('learner_concept_states', sa.Column(name, sa.Integer(), nullable=False, server_default='0'))
    if 'counterexample_last_success_at' not in columns:
        op.add_column('learner_concept_states', sa.Column('counterexample_last_success_at', timestamp))
    if 'counterexample_review_due_at' not in columns:
        op.add_column('learner_concept_states', sa.Column('counterexample_review_due_at', sa.String(40)))
    if 'counterexample_attempts' not in tables:
        op.create_table('counterexample_attempts',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('version_id', sa.String(36), sa.ForeignKey('counterexample_versions.id'), nullable=False),
            sa.Column('validation_id', sa.String(36), sa.ForeignKey('counterexample_validations.id'), nullable=False),
            sa.Column('request_hash', sa.String(64), nullable=False), sa.Column('input_value', sa.JSON(), nullable=False),
            sa.Column('expected_output', sa.JSON(), nullable=False), sa.Column('explanation', sa.Text(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False), sa.Column('lease_token', sa.String(36), nullable=False),
            sa.Column('lease_until', timestamp, nullable=False), sa.Column('result', sa.JSON()),
            sa.Column('execution_report', sa.JSON()), sa.Column('explanation_review', sa.JSON()),
            sa.Column('review_revision', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', timestamp, nullable=False), sa.Column('completed_at', timestamp))
        op.create_index('ix_counterexample_attempts_user_id', 'counterexample_attempts', ['user_id'])
        op.create_index('ix_counterexample_attempts_version_id', 'counterexample_attempts', ['version_id'])
    if 'counterexample_explanation_reviews' not in tables:
        op.create_table('counterexample_explanation_reviews',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('attempt_id', sa.String(36), sa.ForeignKey('counterexample_attempts.id'), nullable=False),
            sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('revision', sa.Integer(), nullable=False), sa.Column('verdict', sa.String(24), nullable=False),
            sa.Column('note', sa.Text(), nullable=False), sa.Column('created_at', timestamp, nullable=False),
            sa.UniqueConstraint('attempt_id', 'revision', name='uq_counterexample_explanation_revision'))
        op.create_index('ix_counterexample_explanation_reviews_attempt_id', 'counterexample_explanation_reviews', ['attempt_id'])


def downgrade():
    op.drop_table('counterexample_explanation_reviews')
    op.drop_table('counterexample_attempts')
    for name in ('counterexample_count', 'counterexample_success', 'counterexample_last_success_at', 'counterexample_review_due_at'):
        op.drop_column('learner_concept_states', name)
    op.drop_column('counterexample_versions', 'blocked_reason')
