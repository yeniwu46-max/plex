"""Separate document publication from indexing; default historical uploads to private."""
from alembic import op
import sqlalchemy as sa

revision = '20261016_0020'
down_revision = '20261016_0019'
branch_labels = None
depends_on = None


def upgrade():
    cols = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('knowledge_documents')}
    fresh = 'visibility' not in cols
    if fresh:
        op.add_column('knowledge_documents', sa.Column('visibility', sa.String(16), nullable=False, server_default='private'))
    if 'class_id' not in cols:
        op.add_column('knowledge_documents', sa.Column('class_id', sa.Integer()))
        op.create_index('ix_knowledge_documents_class_id', 'knowledge_documents', ['class_id'])
    if 'published' not in cols:
        op.add_column('knowledge_documents', sa.Column('published', sa.Boolean(), nullable=False, server_default=sa.false()))
    if fresh:
        # Only system-owned builtin materials have an established public course origin.
        op.execute(sa.text("UPDATE knowledge_documents SET visibility='public', published=1 "
                           "WHERE source='builtin' AND uploaded_by IS NULL"))


def downgrade():
    with op.batch_alter_table('knowledge_documents') as batch:
        batch.drop_index('ix_knowledge_documents_class_id')
        batch.drop_column('published')
        batch.drop_column('class_id')
        batch.drop_column('visibility')
