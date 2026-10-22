"""Tutoring request budgets, cancellation tombstones and model usage records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20261017_0029'
down_revision = '20261017_0028'
branch_labels = None
depends_on = None


def upgrade():
    timestamp = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'ai_runtime_locks' not in tables:
        op.create_table('ai_runtime_locks', sa.Column('scope',sa.String(32),primary_key=True),sa.Column('revision',sa.Integer(),nullable=False))
    if 'tutor_request_cancellations' not in tables:
        op.create_table('tutor_request_cancellations',sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),primary_key=True),
            sa.Column('request_id',sa.String(36),primary_key=True),sa.Column('created_at',timestamp,nullable=False))
    if 'tutor_request_attempts' not in tables:
        op.create_table('tutor_request_attempts',sa.Column('id',sa.String(36),primary_key=True),
            sa.Column('request_id',sa.String(36),sa.ForeignKey('tutor_turns.id'),nullable=False),
            sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('status',sa.String(20),nullable=False),
            sa.Column('started_at',timestamp,nullable=False),sa.Column('lease_until',timestamp,nullable=False),sa.Column('finished_at',timestamp))
        op.create_index('ix_tutor_request_attempts_request_id','tutor_request_attempts',['request_id'])
        op.create_index('ix_tutor_attempt_user_time','tutor_request_attempts',['user_id','started_at'])
        op.create_index('ix_tutor_attempt_capacity','tutor_request_attempts',['status','lease_until'])
    if 'ai_model_calls' not in tables:
        op.create_table('ai_model_calls',sa.Column('id',sa.String(36),primary_key=True),
            sa.Column('workflow',sa.String(32),nullable=False),sa.Column('request_id',sa.String(36),nullable=False),sa.Column('attempt_id',sa.String(36),nullable=False),
            sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('stage',sa.String(32),nullable=False),sa.Column('status',sa.String(20),nullable=False),
            sa.Column('provider',sa.String(64)),sa.Column('model',sa.String(128)),sa.Column('policy_version',sa.String(64),nullable=False),
            sa.Column('state_version',sa.Integer(),nullable=False),sa.Column('retrieval_config_hash',sa.String(64),nullable=False),
            sa.Column('prompt_tokens',sa.Integer()),sa.Column('completion_tokens',sa.Integer()),sa.Column('total_tokens',sa.Integer()),
            sa.Column('error_code',sa.String(64)),sa.Column('elapsed_ms',sa.Integer()),sa.Column('started_at',timestamp,nullable=False),sa.Column('finished_at',timestamp))
        op.create_index('ix_ai_model_calls_request_id','ai_model_calls',['request_id'])
        op.create_index('ix_ai_call_user_time','ai_model_calls',['user_id','started_at'])


def downgrade():
    for table in ['ai_model_calls','tutor_request_attempts','tutor_request_cancellations','ai_runtime_locks']:
        op.drop_table(table)
