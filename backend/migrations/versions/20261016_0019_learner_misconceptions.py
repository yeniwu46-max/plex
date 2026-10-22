"""Reviewable misconception candidates with immutable event links."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = '20261016_0019'
down_revision = '20261015_0018'
branch_labels = None
depends_on = None
timestamp = sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql')


def upgrade():
    existing = sa.inspect(op.get_bind()).get_table_names()
    if 'learner_misconceptions' not in existing:
        op.create_table('learner_misconceptions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('state_id', sa.Integer(), sa.ForeignKey('learner_states.id'), nullable=False),
            sa.Column('concept_id', sa.String(80), nullable=False),
            sa.Column('kind', sa.String(64), nullable=False),
            sa.Column('status', sa.String(16), nullable=False),
            sa.Column('revision', sa.Integer(), nullable=False),
            sa.Column('updated_version', sa.Integer(), nullable=False),
            sa.Column('manual_status', sa.String(16)),
            sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('review_note', sa.String(300)),
            sa.Column('reviewed_at', timestamp),
            sa.Column('last_signal_at', timestamp, nullable=False),
            sa.Column('updated_at', timestamp, nullable=False),
            sa.UniqueConstraint('state_id', 'concept_id', 'kind', name='uq_state_misconception'))
        op.create_index('ix_learner_misconceptions_state_id', 'learner_misconceptions', ['state_id'])
    if 'learner_misconception_evidence' not in existing:
        op.create_table('learner_misconception_evidence',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('misconception_id', sa.Integer(), sa.ForeignKey('learner_misconceptions.id'), nullable=False),
            sa.Column('event_id', sa.Integer(), sa.ForeignKey('learning_events.id'), nullable=False),
            sa.Column('question_id', sa.Integer(), nullable=False),
            sa.Column('observation', sa.String(240), nullable=False),
            sa.UniqueConstraint('misconception_id', 'event_id', name='uq_misconception_event'))
        op.create_index('ix_learner_misconception_evidence_misconception_id',
                        'learner_misconception_evidence', ['misconception_id'])


def downgrade():
    op.drop_table('learner_misconception_evidence')
    op.drop_table('learner_misconceptions')
