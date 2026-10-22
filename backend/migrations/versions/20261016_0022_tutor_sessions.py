"""Task-scoped tutor sessions and idempotent validated turns."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20261016_0022'
down_revision = '20261016_0021'
branch_labels = None
depends_on = None


def upgrade():
    timestamp = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'tutor_sessions' not in tables:
        op.create_table('tutor_sessions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('question_ref', sa.String(100)), sa.Column('question_version', sa.String(64)),
            sa.Column('lease_token', sa.String(36)), sa.Column('lease_until', timestamp),
            sa.Column('created_at', timestamp, nullable=False))
        op.create_index('ix_tutor_sessions_user_id', 'tutor_sessions', ['user_id'])
    if 'tutor_turns' not in tables:
        op.create_table('tutor_turns',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('session_id', sa.String(36), sa.ForeignKey('tutor_sessions.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('request_hash', sa.String(64), nullable=False), sa.Column('code_hash', sa.String(64), nullable=False),
            sa.Column('question', sa.Text(), nullable=False), sa.Column('mode', sa.String(32), nullable=False),
            sa.Column('status', sa.String(16), nullable=False), sa.Column('lease_token', sa.String(36), nullable=False),
            sa.Column('lease_until', timestamp, nullable=False), sa.Column('response', sa.JSON()),
            sa.Column('evidence_refs', sa.JSON(), nullable=False),
            sa.Column('receipt_id', sa.String(36), sa.ForeignKey('tutor_display_receipts.id')),
            sa.Column('error_code', sa.String(60)), sa.Column('created_at', timestamp, nullable=False),
            sa.Column('completed_at', timestamp))
        op.create_index('ix_tutor_turns_session_id', 'tutor_turns', ['session_id'])
        op.create_index('ix_tutor_turns_user_id', 'tutor_turns', ['user_id'])


def downgrade():
    op.drop_table('tutor_turns')
    op.drop_table('tutor_sessions')
