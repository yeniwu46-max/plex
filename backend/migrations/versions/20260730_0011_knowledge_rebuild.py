"""Knowledge point rebuild: 8 domains / ~25 nodes, and promote `problems` into
the single unified question bank (coding + mcq) so the whole bank is editable
from one SQL table.

- new table `knowledge_nodes`: DB-side mirror of app/data/knowledge_node_registry.py
- `problems` gains question-type, node binding, mcq/coding payload and review
  bookkeeping columns
- `problems.title_en` / `concept_group` become nullable because questions merged
  in from the MCQ banks and the frontend static bank have no English title and
  no legacy A-G concept letter.

Revision ID: 20260730_0011
Revises: 20260730_0010
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260730_0011'
down_revision = '20260730_0010'
branch_labels = None
depends_on = None


NEW_PROBLEM_COLUMNS = (
    ('question_type', lambda: sa.Column('question_type', sa.String(16), nullable=False, server_default='coding')),
    ('kg_node_id', lambda: sa.Column('kg_node_id', sa.String(48))),
    ('domain_key', lambda: sa.Column('domain_key', sa.String(32))),
    ('options_json', lambda: sa.Column('options_json', sa.JSON())),
    ('correct_index', lambda: sa.Column('correct_index', sa.Integer())),
    ('test_cases_json', lambda: sa.Column('test_cases_json', sa.JSON())),
    ('starter_code', lambda: sa.Column('starter_code', sa.Text())),
    ('run_mode', lambda: sa.Column('run_mode', sa.String(16))),
    ('hint', lambda: sa.Column('hint', sa.Text())),
    ('source_kind', lambda: sa.Column('source_kind', sa.String(24), nullable=False, server_default='legacy_bank')),
    ('source_ref', lambda: sa.Column('source_ref', sa.String(128))),
    ('merged_from_json', lambda: sa.Column('merged_from_json', sa.JSON())),
    ('needs_review', lambda: sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.false())),
    ('review_note', lambda: sa.Column('review_note', sa.Text())),
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'knowledge_nodes' not in tables:
        op.create_table(
            'knowledge_nodes',
            sa.Column('id', sa.String(48), primary_key=True),
            sa.Column('domain_key', sa.String(32), nullable=False),
            sa.Column('domain_title', sa.String(64), nullable=False),
            sa.Column('domain_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('title', sa.String(64), nullable=False),
            sa.Column('summary', sa.String(255)),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('level', sa.String(16), nullable=False, server_default='basic'),
            sa.Column('default_difficulty', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('knowledge_keys_json', sa.JSON()),
            sa.Column('legacy_kg_ids_json', sa.JSON()),
            sa.Column('document_id', sa.String(64)),
            sa.Column('pos_x', sa.Integer()),
            sa.Column('pos_y', sa.Integer()),
        )
        op.create_index('ix_knowledge_nodes_domain_key', 'knowledge_nodes', ['domain_key'])

    if 'problems' in tables:
        existing = {col['name'] for col in inspector.get_columns('problems')}
        with op.batch_alter_table('problems') as batch:
            for name, factory in NEW_PROBLEM_COLUMNS:
                if name not in existing:
                    batch.add_column(factory())
            # 合并进来的选择题/前端静态题没有英文标题，也没有旧系统的 A-G 分组字母
            batch.alter_column('title_en', existing_type=sa.String(200), nullable=True)
            batch.alter_column('concept_group', existing_type=sa.String(1), nullable=True)

        cols_now = {col['name'] for col in sa.inspect(bind).get_columns('problems')}
        index_names = {idx['name'] for idx in sa.inspect(bind).get_indexes('problems')}
        if 'kg_node_id' in cols_now and 'ix_problems_kg_node_id' not in index_names:
            op.create_index('ix_problems_kg_node_id', 'problems', ['kg_node_id'])
        if 'domain_key' in cols_now and 'ix_problems_domain_key' not in index_names:
            op.create_index('ix_problems_domain_key', 'problems', ['domain_key'])
        if 'question_type' in cols_now and 'ix_problems_question_type' not in index_names:
            op.create_index('ix_problems_question_type', 'problems', ['question_type'])
        if 'needs_review' in cols_now and 'ix_problems_needs_review' not in index_names:
            op.create_index('ix_problems_needs_review', 'problems', ['needs_review'])


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if 'problems' in tables:
        index_names = {idx['name'] for idx in sa.inspect(bind).get_indexes('problems')}
        for name in (
            'ix_problems_needs_review',
            'ix_problems_question_type',
            'ix_problems_domain_key',
            'ix_problems_kg_node_id',
        ):
            if name in index_names:
                op.drop_index(name, table_name='problems')

        existing = {col['name'] for col in sa.inspect(bind).get_columns('problems')}
        with op.batch_alter_table('problems') as batch:
            for name, _factory in reversed(NEW_PROBLEM_COLUMNS):
                if name in existing:
                    batch.drop_column(name)
            batch.alter_column('title_en', existing_type=sa.String(200), nullable=False)
            batch.alter_column('concept_group', existing_type=sa.String(1), nullable=False)

    if 'knowledge_nodes' in tables:
        op.drop_table('knowledge_nodes')
