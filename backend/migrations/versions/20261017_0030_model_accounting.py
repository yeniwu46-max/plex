"""Attach trusted class scope and prompt fingerprint to new model accounting."""
from alembic import op
import sqlalchemy as sa
revision='20261017_0030'
down_revision='20261017_0029'
branch_labels=None
depends_on=None

def upgrade():
    names={c['name'] for c in sa.inspect(op.get_bind()).get_columns('ai_model_calls')}
    if 'class_id' not in names:op.add_column('ai_model_calls',sa.Column('class_id',sa.Integer(),nullable=True))
    if 'prompt_hash' not in names:op.add_column('ai_model_calls',sa.Column('prompt_hash',sa.String(64),nullable=True))
    if 'ix_ai_call_class_time' not in {i['name'] for i in sa.inspect(op.get_bind()).get_indexes('ai_model_calls')}:
        op.create_index('ix_ai_call_class_time','ai_model_calls',['class_id','started_at'])

def downgrade():
    op.drop_index('ix_ai_call_class_time',table_name='ai_model_calls')
    op.drop_column('ai_model_calls','prompt_hash')
    op.drop_column('ai_model_calls','class_id')
