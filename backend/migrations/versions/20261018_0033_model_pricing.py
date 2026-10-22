"""Frozen model-price estimates; historical unknowns stay unknown."""
from alembic import op
import sqlalchemy as sa

revision = '20261018_0033'
down_revision = '20261018_0032'
branch_labels = None
depends_on = None


def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('ai_model_calls')}
    for name, column_type in (
        ('cached_input_tokens', sa.Integer()), ('cost_status', sa.String(32)), ('cost_currency', sa.String(3)),
        ('cost_min', sa.Numeric(20, 10)), ('cost_max', sa.Numeric(20, 10)), ('price_snapshot', sa.JSON())):
        if name not in columns:
            op.add_column('ai_model_calls', sa.Column(name, column_type, nullable=True))


def downgrade():
    for name in ('price_snapshot', 'cost_max', 'cost_min', 'cost_currency', 'cost_status', 'cached_input_tokens'):
        op.drop_column('ai_model_calls', name)
