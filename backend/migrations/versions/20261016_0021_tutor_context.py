"""Owned execution references and server-owned task help policy."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20261016_0021'
down_revision = '20261016_0020'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if 'tutoring_policy' not in {c['name'] for c in inspector.get_columns('trials')}:
        op.add_column('trials', sa.Column('tutoring_policy', sa.String(20), nullable=False, server_default='auto'))
    if 'tutor_code_runs' not in inspector.get_table_names():
        op.create_table('tutor_code_runs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('question_ref', sa.String(100)), sa.Column('question_version', sa.String(64)),
            sa.Column('code_hash', sa.String(64), nullable=False),
            sa.Column('normalized_code_hash', sa.String(64), nullable=False),
            sa.Column('execution_kind', sa.String(20), nullable=False),
            sa.Column('backend', sa.String(32), nullable=False), sa.Column('result', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'), nullable=False))
        op.create_index('ix_tutor_code_runs_user_id', 'tutor_code_runs', ['user_id'])
        op.create_index('ix_tutor_code_runs_created_at', 'tutor_code_runs', ['created_at'])


def downgrade():
    op.drop_table('tutor_code_runs')
    with op.batch_alter_table('trials') as batch:
        batch.drop_column('tutoring_policy')
