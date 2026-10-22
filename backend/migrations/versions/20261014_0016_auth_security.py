"""Authentication recovery, session versions and shared request limits."""
from alembic import op
import sqlalchemy as sa

revision = '20261014_0016'
down_revision = '20260928_0015'
branch_labels = None
depends_on = None


def upgrade():
    existing = sa.inspect(op.get_bind()).get_table_names()
    if 'oauth_identities' not in existing:
        op.create_table('oauth_identities', sa.Column('identity_key', sa.String(160), primary_key=True), sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False))
    if 'auth_session_states' not in existing:
        op.create_table('auth_session_states', sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True), sa.Column('version', sa.Integer(), nullable=False))
    if 'auth_tokens' not in existing:
        op.create_table('auth_tokens', sa.Column('token_hash', sa.String(64), primary_key=True), sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False), sa.Column('purpose', sa.String(20), nullable=False), sa.Column('version', sa.Integer(), nullable=False), sa.Column('expires_at', sa.DateTime(), nullable=False))
        op.create_index('ix_auth_tokens_expires_at', 'auth_tokens', ['expires_at'])
    if 'auth_rate_limits' not in existing:
        op.create_table('auth_rate_limits', sa.Column('key_hash', sa.String(64), primary_key=True), sa.Column('attempts', sa.Integer(), nullable=False), sa.Column('expires_at', sa.DateTime(), nullable=False))
        op.create_index('ix_auth_rate_limits_expires_at', 'auth_rate_limits', ['expires_at'])


def downgrade():
    for table in ('oauth_identities', 'auth_rate_limits', 'auth_tokens', 'auth_session_states'):
        op.drop_table(table)
