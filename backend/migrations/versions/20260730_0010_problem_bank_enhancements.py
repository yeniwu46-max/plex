"""Problem bank follow-up enhancements: background provenance, has_english,
star_difficulty, time_limit_ms, samples_source columns on `problems`, plus
new `problem_tags` / `problem_tag_map` tables (Luogu-style tag system).

See backend/scripts/problem_bank_import/REPORT.md (增强篇) for the full
field-design write-up.

Revision ID: 20260730_0010
Revises: 20260730_0009
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260730_0010'
down_revision = '20260730_0009'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'problems' in tables:
        existing_cols = {col['name'] for col in inspector.get_columns('problems')}
        with op.batch_alter_table('problems') as batch:
            if 'background_source' not in existing_cols:
                batch.add_column(sa.Column('background_source', sa.String(32)))
            if 'has_english' not in existing_cols:
                batch.add_column(sa.Column('has_english', sa.Boolean(), nullable=False, server_default=sa.false()))
            if 'samples_source' not in existing_cols:
                batch.add_column(sa.Column('samples_source', sa.String(64)))
            if 'star_difficulty' not in existing_cols:
                batch.add_column(sa.Column('star_difficulty', sa.SmallInteger()))
            if 'time_limit_ms' not in existing_cols:
                batch.add_column(sa.Column('time_limit_ms', sa.Integer()))

    tables = set(sa.inspect(bind).get_table_names())
    if 'problem_tags' not in tables:
        op.create_table(
            'problem_tags',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('code', sa.String(64), nullable=False),
            sa.Column('label', sa.String(50), nullable=False),
            sa.Column('tag_type', sa.String(16), nullable=False),
            sa.Column('color', sa.String(16)),
            sa.Column('sort_order', sa.Integer(), server_default='0'),
            sa.UniqueConstraint('code', name='uq_problem_tags_code'),
        )
        op.create_index('ix_problem_tags_code', 'problem_tags', ['code'])
        op.create_index('ix_problem_tags_tag_type', 'problem_tags', ['tag_type'])

    tables = set(sa.inspect(bind).get_table_names())
    if 'problem_tag_map' not in tables:
        op.create_table(
            'problem_tag_map',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('problem_id', sa.Integer(), sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tag_id', sa.Integer(), sa.ForeignKey('problem_tags.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('problem_id', 'tag_id', name='uq_problem_tag'),
        )
        op.create_index('ix_problem_tag_map_problem_id', 'problem_tag_map', ['problem_id'])
        op.create_index('ix_problem_tag_map_tag_id', 'problem_tag_map', ['tag_id'])


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if 'problem_tag_map' in tables:
        op.drop_table('problem_tag_map')
    if 'problem_tags' in tables:
        op.drop_table('problem_tags')
    if 'problems' in tables:
        existing_cols = {col['name'] for col in sa.inspect(bind).get_columns('problems')}
        with op.batch_alter_table('problems') as batch:
            if 'time_limit_ms' in existing_cols:
                batch.drop_column('time_limit_ms')
            if 'star_difficulty' in existing_cols:
                batch.drop_column('star_difficulty')
            if 'samples_source' in existing_cols:
                batch.drop_column('samples_source')
            if 'has_english' in existing_cols:
                batch.drop_column('has_english')
            if 'background_source' in existing_cols:
                batch.drop_column('background_source')
