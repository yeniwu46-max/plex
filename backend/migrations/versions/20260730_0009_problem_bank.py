"""Add standardized problem bank tables (problems, problem_submissions,
problem_legacy_quest_map) imported from the legacy Mulberry/HydroOJ dump.

See backend/scripts/problem_bank_import/REPORT.md for the full cleaning /
field-design write-up.

Revision ID: 20260730_0009
Revises: 20260729_0008
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260730_0009'
down_revision = '20260729_0008'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if 'problems' not in tables:
        op.create_table(
            'problems',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=False),
            sa.Column('problem_no', sa.String(8), nullable=False),
            sa.Column('concept', sa.String(50)),
            sa.Column('concept_group', sa.String(1), nullable=False),
            sa.Column('title_en', sa.String(200), nullable=False),
            sa.Column('title_cn', sa.String(200), nullable=False),
            sa.Column('background', sa.Text()),
            sa.Column('description_en', sa.Text()),
            sa.Column('description_cn', sa.Text()),
            sa.Column('input_format_en', sa.Text()),
            sa.Column('output_format_en', sa.Text()),
            sa.Column('input_format_cn', sa.Text()),
            sa.Column('output_format_cn', sa.Text()),
            sa.Column('samples_json', sa.JSON()),
            sa.Column('notes_json', sa.JSON()),
            sa.Column('difficulty', sa.Integer()),
            sa.Column('level', sa.Integer()),
            sa.Column('topic', sa.Integer()),
            sa.Column('reference_answer', sa.Text()),
            sa.Column('template', sa.Text()),
            sa.Column('legacy_problem_name', sa.String(100)),
            sa.Column('legacy_author_user_id', sa.Integer()),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('problem_no', name='uq_problems_problem_no'),
        )
        op.create_index('ix_problems_concept_group', 'problems', ['concept_group'])
        op.create_index('ix_problems_is_active', 'problems', ['is_active'])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'problem_legacy_quest_map' not in tables:
        op.create_table(
            'problem_legacy_quest_map',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('problem_id', sa.Integer(), sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
            sa.Column('legacy_quest_id', sa.Integer(), nullable=False),
            sa.Column('legacy_quest_title_cn', sa.String(100)),
            sa.Column('required', sa.Boolean()),
            sa.Column('sort_order', sa.Integer(), server_default='0'),
        )
        op.create_index('ix_quest_map_problem_id', 'problem_legacy_quest_map', ['problem_id'])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'problem_submissions' not in tables:
        op.create_table(
            'problem_submissions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=False),
            sa.Column('problem_id', sa.Integer(), sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
            sa.Column('legacy_user_id', sa.Integer(), nullable=False),
            sa.Column('legacy_username', sa.String(100)),
            sa.Column('legacy_student_name', sa.String(50)),
            sa.Column('legacy_group_id', sa.Integer()),
            sa.Column('legacy_group_name', sa.String(150)),
            sa.Column('code_content', sa.Text(), nullable=False),
            sa.Column('status', sa.String(8), nullable=False),
            sa.Column('is_accepted', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('compile_success', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('test_success', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('score_points', sa.Integer()),
            sa.Column('score_total', sa.Integer()),
            sa.Column('score_percent', sa.Numeric(5, 1)),
            sa.Column('test_case_results_json', sa.JSON()),
            sa.Column('raw_judge_output', sa.Text()),
            sa.Column('exec_time_ms', sa.Integer()),
            sa.Column('exec_memory_kb', sa.Integer()),
            sa.Column('time_spent_seconds', sa.Integer()),
            sa.Column('self_confidence', sa.Integer()),
            sa.Column('legacy_error_name', sa.String(100)),
            sa.Column('returncode', sa.Integer()),
            sa.Column('legacy_prev_solution_id', sa.Integer()),
            sa.Column('submitted_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_submissions_problem_id', 'problem_submissions', ['problem_id'])
        op.create_index('ix_submissions_legacy_user_id', 'problem_submissions', ['legacy_user_id'])
        op.create_index('ix_submissions_status', 'problem_submissions', ['status'])
        op.create_index('ix_submissions_problem_user', 'problem_submissions', ['problem_id', 'legacy_user_id'])


def downgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'problem_submissions' in tables:
        op.drop_table('problem_submissions')
    if 'problem_legacy_quest_map' in tables:
        op.drop_table('problem_legacy_quest_map')
    if 'problems' in tables:
        op.drop_table('problems')
