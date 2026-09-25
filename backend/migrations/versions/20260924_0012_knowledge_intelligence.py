"""Knowledge Intelligence Layer (Graph-enhanced RAG).

New tables:
- knowledge_concepts / knowledge_relations : multi-type knowledge graph stored in MySQL
- knowledge_documents / knowledge_chunks / knowledge_index_jobs : document registry, chunk
  metadata and async index state machine (embeddings live in the VectorStore, joined by chunk_id)
- rag_query_logs : privacy-preserving RAG request logs (query preview only)

Revision ID: 20260924_0012
Revises: 20260730_0011
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa

revision = '20260924_0012'
down_revision = '20260730_0011'
branch_labels = None
depends_on = None


def _timestamps():
    return (
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'knowledge_concepts' not in tables:
        op.create_table(
            'knowledge_concepts',
            sa.Column('concept_id', sa.String(64), primary_key=True),
            sa.Column('name', sa.String(160), nullable=False, index=True),
            sa.Column('description', sa.Text()),
            sa.Column('course_id', sa.String(64), nullable=False, server_default='python-basics', index=True),
            sa.Column('chapter', sa.String(120), index=True),
            sa.Column('node_type', sa.String(24), nullable=False, server_default='concept', index=True),
            sa.Column('difficulty', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
            sa.Column('learning_objectives', sa.JSON()),
            sa.Column('common_misconceptions', sa.JSON()),
            sa.Column('tags', sa.JSON()),
            sa.Column('mastery_threshold', sa.Float(), nullable=False, server_default='0.7'),
            sa.Column('embedding_text', sa.Text()),
            sa.Column('source', sa.String(32), nullable=False, server_default='registry'),
            sa.Column('status', sa.String(16), nullable=False, server_default='active'),
            sa.Column('kg_node_id', sa.String(48), index=True),
            sa.Column('ref_type', sa.String(32)),
            sa.Column('ref_id', sa.String(64)),
            *_timestamps(),
        )

    if 'knowledge_relations' not in tables:
        op.create_table(
            'knowledge_relations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'source_id', sa.String(64),
                sa.ForeignKey('knowledge_concepts.concept_id', ondelete='CASCADE'), nullable=False, index=True,
            ),
            sa.Column(
                'target_id', sa.String(64),
                sa.ForeignKey('knowledge_concepts.concept_id', ondelete='CASCADE'), nullable=False, index=True,
            ),
            sa.Column('relation_type', sa.String(24), nullable=False, index=True),
            sa.Column('weight', sa.Float(), nullable=False, server_default='1'),
            sa.Column('source', sa.String(32), nullable=False, server_default='registry'),
            sa.Column('teacher_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('verified_by', sa.Integer()),
            sa.Column('note', sa.String(255)),
            *_timestamps(),
            sa.UniqueConstraint('source_id', 'target_id', 'relation_type', name='uq_knowledge_relation'),
        )

    if 'knowledge_documents' not in tables:
        op.create_table(
            'knowledge_documents',
            sa.Column('id', sa.String(32), primary_key=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('file_name', sa.String(255)),
            sa.Column('file_path', sa.String(500)),
            sa.Column('file_type', sa.String(16), nullable=False, server_default='md'),
            sa.Column('file_size', sa.Integer(), server_default='0'),
            sa.Column('checksum', sa.String(64), index=True),
            sa.Column('course_id', sa.String(64), nullable=False, server_default='python-basics', index=True),
            sa.Column('chapter', sa.String(120)),
            sa.Column('resource_type', sa.String(32), nullable=False, server_default='markdown'),
            sa.Column('source', sa.String(64), server_default='upload'),
            sa.Column('audience_level', sa.String(24), server_default='beginner'),
            sa.Column('uploaded_by', sa.Integer(), index=True),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('status', sa.String(16), nullable=False, server_default='PENDING', index=True),
            sa.Column('stage_progress', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_message', sa.Text()),
            sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('concept_ids', sa.JSON()),
            sa.Column('teacher_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('verified_by', sa.Integer()),
            sa.Column('verified_at', sa.DateTime()),
            sa.Column('quality_score', sa.Float(), nullable=False, server_default='0.6'),
            sa.Column('meta', sa.JSON()),
            sa.Column('indexed_at', sa.DateTime()),
            *_timestamps(),
        )

    if 'knowledge_chunks' not in tables:
        op.create_table(
            'knowledge_chunks',
            sa.Column('chunk_id', sa.String(32), primary_key=True),
            sa.Column(
                'document_id', sa.String(32),
                sa.ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False, index=True,
            ),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('title', sa.String(255)),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('content_hash', sa.String(64), index=True),
            sa.Column('knowledge_type', sa.String(32), nullable=False, server_default='concept_explanation', index=True),
            sa.Column('concept_ids', sa.JSON()),
            sa.Column('primary_concept_id', sa.String(64), index=True),
            sa.Column('course_id', sa.String(64), nullable=False, server_default='python-basics', index=True),
            sa.Column('chapter', sa.String(120)),
            sa.Column('difficulty', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('resource_type', sa.String(32), nullable=False, server_default='markdown'),
            sa.Column('source', sa.String(255)),
            sa.Column('source_page', sa.Integer()),
            sa.Column('audience_level', sa.String(24), server_default='beginner'),
            sa.Column('teacher_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('embedding_status', sa.String(16), nullable=False, server_default='PENDING'),
            sa.Column('embedding_model', sa.String(80)),
            sa.Column('status', sa.String(16), nullable=False, server_default='active', index=True),
            sa.Column('meta', sa.JSON()),
            *_timestamps(),
        )

    if 'knowledge_index_jobs' not in tables:
        op.create_table(
            'knowledge_index_jobs',
            sa.Column('id', sa.String(32), primary_key=True),
            sa.Column(
                'document_id', sa.String(32),
                sa.ForeignKey('knowledge_documents.id', ondelete='CASCADE'), nullable=False, index=True,
            ),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('status', sa.String(16), nullable=False, server_default='PENDING', index=True),
            sa.Column('stage', sa.String(16), nullable=False, server_default='PENDING'),
            sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('embedded_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_message', sa.Text()),
            sa.Column('triggered_by', sa.Integer()),
            sa.Column('embedding_provider', sa.String(64)),
            sa.Column('vector_backend', sa.String(32)),
            sa.Column('started_at', sa.DateTime()),
            sa.Column('finished_at', sa.DateTime()),
            *_timestamps(),
        )

    if 'rag_query_logs' not in tables:
        op.create_table(
            'rag_query_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), index=True),
            sa.Column('role', sa.String(16)),
            sa.Column('scene', sa.String(32), server_default='chat', index=True),
            sa.Column('query_hash', sa.String(64), index=True),
            sa.Column('query_preview', sa.String(200)),
            sa.Column('intent', sa.String(32)),
            sa.Column('detected_concepts', sa.JSON()),
            sa.Column('graph_nodes', sa.JSON()),
            sa.Column('retrieved_chunks', sa.JSON()),
            sa.Column('retrieval_scores', sa.JSON()),
            sa.Column('rerank_scores', sa.JSON()),
            sa.Column('teaching_strategy', sa.JSON()),
            sa.Column('hint_level', sa.Integer()),
            sa.Column('model', sa.String(80)),
            sa.Column('provider', sa.String(40)),
            sa.Column('generation_mode', sa.String(24)),
            sa.Column('latency_ms', sa.Integer()),
            sa.Column('token_usage', sa.JSON()),
            sa.Column('confidence', sa.Float()),
            sa.Column('confidence_level', sa.String(16)),
            sa.Column('knowledge_grounded', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('status', sa.String(16), nullable=False, server_default='ok'),
            sa.Column('error_message', sa.String(255)),
            sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        )


def downgrade():
    for table in (
        'rag_query_logs',
        'knowledge_index_jobs',
        'knowledge_chunks',
        'knowledge_documents',
        'knowledge_relations',
        'knowledge_concepts',
    ):
        op.drop_table(table)
