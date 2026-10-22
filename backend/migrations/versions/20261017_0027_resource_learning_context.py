"""Bind resource generation to a frozen profile and versioned learner state."""
from alembic import op
import sqlalchemy as sa

revision = '20261017_0027'
down_revision = '20261017_0026'
branch_labels = None
depends_on = None


def upgrade():
    present = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('resource_generation_tasks')}
    for name,kind in (('context_snapshot',sa.JSON()),('context_hash',sa.String(64))):
        if name not in present:
            op.add_column('resource_generation_tasks',sa.Column(name,kind,nullable=True))


def downgrade():
    op.drop_column('resource_generation_tasks','context_hash')
    op.drop_column('resource_generation_tasks','context_snapshot')
