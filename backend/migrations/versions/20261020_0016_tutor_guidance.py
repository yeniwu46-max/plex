"""Persist idempotent tutor requests and display confirmations."""
from alembic import op
import sqlalchemy as sa

revision = '20261020_0016'
down_revision = '20260928_0015'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tutor_guidance_turns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('scope_hash', sa.String(64), nullable=False),
        sa.Column('focus', sa.String(40), nullable=False),
        sa.Column('mode', sa.String(24), nullable=False),
        sa.Column('stage', sa.Integer(), nullable=False),
        sa.Column('result', sa.JSON()),
        sa.Column('lease_token', sa.String(36)),
        sa.Column('lease_expires_at', sa.DateTime()),
        sa.Column('displayed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'request_id', name='uq_tutor_guidance_request'),
    )


def downgrade():
    op.drop_table('tutor_guidance_turns')
