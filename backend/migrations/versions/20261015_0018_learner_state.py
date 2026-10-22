"""Durable learner evidence and versioned state, without historical backfill."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
revision = '20261015_0018'
down_revision = '20261014_0017'
branch_labels = None
depends_on = None

def upgrade():
    existing = sa.inspect(op.get_bind()).get_table_names()
    if 'learning_events' not in existing:
        op.create_table('learning_events',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('course', sa.String(length=40), nullable=False),
            sa.Column('dedupe_key', sa.String(length=64), nullable=False, unique=True),
            sa.Column('kind', sa.String(length=40), nullable=False),
            sa.Column('source_type', sa.String(length=40), nullable=False),
            sa.Column('source_id', sa.String(length=80), nullable=False),
            sa.Column('source_version', sa.String(length=64), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=False),
            sa.Column('occurred_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=False),
            sa.Column('created_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False),
            sa.Column('attempts', sa.Integer(), nullable=False),
            sa.Column('lease_token', sa.String(length=36), nullable=True),
            sa.Column('lease_until', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=True),
            sa.Column('retry_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=True),
            sa.Column('error_code', sa.String(length=80), nullable=True),
            sa.Column('processed_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=True),
        )
        op.create_index('ix_learning_events_user_id', 'learning_events', ['user_id'], unique=False)
        op.create_index('ix_learning_events_lease_until', 'learning_events', ['lease_until'], unique=False)
        op.create_index('ix_learning_events_status', 'learning_events', ['status'], unique=False)
    if 'learner_states' not in existing:
        op.create_table('learner_states',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('course', sa.String(length=40), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('policy_version', sa.String(length=40), nullable=False),
            sa.Column('updated_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=False),
            sa.UniqueConstraint('user_id', 'course', name='uq_learner_state_course'),
        )
    if 'learner_concept_states' not in existing:
        op.create_table('learner_concept_states',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('state_id', sa.Integer(), sa.ForeignKey('learner_states.id'), nullable=False),
            sa.Column('concept_id', sa.String(length=80), nullable=False),
            sa.Column('independent_count', sa.Integer(), nullable=False),
            sa.Column('independent_success', sa.Integer(), nullable=False),
            sa.Column('assisted_count', sa.Integer(), nullable=False),
            sa.Column('assisted_success', sa.Integer(), nullable=False),
            sa.Column('hints_seen', sa.Integer(), nullable=False),
            sa.Column('review_count', sa.Integer(), nullable=False),
            sa.Column('review_due_at', sa.String(length=40), nullable=True),
            sa.Column('review_updated_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=True),
            sa.Column('last_evidence_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=True),
            sa.UniqueConstraint('state_id', 'concept_id', name='uq_learner_concept'),
        )
    if 'learner_state_changes' not in existing:
        op.create_table('learner_state_changes',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('state_id', sa.Integer(), sa.ForeignKey('learner_states.id'), nullable=False),
            sa.Column('event_id', sa.Integer(), sa.ForeignKey('learning_events.id'), nullable=False, unique=True),
            sa.Column('base_version', sa.Integer(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('producer_version', sa.String(length=40), nullable=False),
            sa.Column('reason', sa.String(length=240), nullable=False),
            sa.Column('changes', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=False),
            sa.UniqueConstraint('state_id', 'version', name='uq_state_change_version'),
        )
        op.create_index('ix_learner_state_changes_state_id', 'learner_state_changes', ['state_id'], unique=False)
    if 'tutor_display_receipts' not in existing:
        op.create_table('tutor_display_receipts',
            sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('course', sa.String(length=40), nullable=False),
            sa.Column('question_id', sa.Integer(), sa.ForeignKey('trial_questions.id'), nullable=True),
            sa.Column('concept_id', sa.String(length=80), nullable=True),
            sa.Column('mode', sa.String(length=32), nullable=False),
            sa.Column('response_hash', sa.String(length=64), nullable=False),
            sa.Column('created_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=False),
            sa.Column('displayed_at', sa.DateTime().with_variant(DATETIME(fsp=6), 'mysql'), nullable=True),
        )
        op.create_index('ix_tutor_display_receipts_user_id', 'tutor_display_receipts', ['user_id'], unique=False)


def downgrade():
    op.drop_table('tutor_display_receipts')
    op.drop_table('learner_state_changes')
    op.drop_table('learner_concept_states')
    op.drop_table('learner_states')
    op.drop_table('learning_events')
