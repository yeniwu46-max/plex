"""Immutable provenance for teacher-loaded and adapted catalog drafts."""
from alembic import op
import sqlalchemy as sa

revision='20261017_0026'
down_revision='20261016_0025'
branch_labels=None
depends_on=None


def upgrade():
    if 'source_template' not in {column['name'] for column in sa.inspect(op.get_bind()).get_columns('counterexample_versions')}:
        op.add_column('counterexample_versions',sa.Column('source_template',sa.JSON()))


def downgrade():
    op.drop_column('counterexample_versions','source_template')
