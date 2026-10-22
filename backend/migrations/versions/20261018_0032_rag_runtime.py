"""Independent RAG admission and recoverable owner-only results."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '20261018_0032'
down_revision = '20261018_0031'
branch_labels = None
depends_on = None


def upgrade():
    timestamp = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'rag_requests' not in tables:
        op.create_table('rag_requests', sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('role', sa.String(20), nullable=False), sa.Column('body_hash', sa.String(64), nullable=False),
            sa.Column('policy_version', sa.String(64), nullable=False), sa.Column('status', sa.String(20), nullable=False),
            sa.Column('lease_token', sa.String(36), nullable=False), sa.Column('lease_until', timestamp, nullable=False),
            sa.Column('response', sa.JSON()), sa.Column('evidence_refs', sa.JSON()), sa.Column('error_code', sa.String(64)),
            sa.Column('created_at', timestamp, nullable=False), sa.Column('completed_at', timestamp))
    if 'rag_request_attempts' not in tables:
        op.create_table('rag_request_attempts', sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('request_id', sa.String(36), sa.ForeignKey('rag_requests.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('status', sa.String(20), nullable=False), sa.Column('started_at', timestamp, nullable=False),
            sa.Column('lease_until', timestamp, nullable=False), sa.Column('finished_at', timestamp))
    for name, table, columns in (
        ('ix_rag_requests_user_id', 'rag_requests', ['user_id']),
        ('ix_rag_request_attempts_request_id', 'rag_request_attempts', ['request_id']),
        ('ix_rag_attempt_user_time', 'rag_request_attempts', ['user_id', 'started_at']),
        ('ix_rag_attempt_capacity', 'rag_request_attempts', ['status', 'lease_until'])):
        if name not in {i['name'] for i in sa.inspect(op.get_bind()).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade():
    op.drop_table('rag_request_attempts')
    op.drop_table('rag_requests')
