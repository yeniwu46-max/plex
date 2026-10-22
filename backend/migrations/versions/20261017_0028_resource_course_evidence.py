"""Record immutable resource evidence provenance without backfilling history."""
from alembic import op
import sqlalchemy as sa

revision = '20261017_0028'
down_revision = '20261017_0027'
branch_labels = None
depends_on = None


def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('resource_generation_tasks')}
    if 'evidence_manifest' not in columns:
        op.add_column('resource_generation_tasks', sa.Column('evidence_manifest', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('resource_generation_tasks', 'evidence_manifest')
