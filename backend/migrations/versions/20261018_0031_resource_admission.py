"""Persist resource admission scope and request identity without historical guesses."""
from alembic import op
import sqlalchemy as sa
revision='20261018_0031'
down_revision='20261017_0030'
branch_labels=None
depends_on=None


def upgrade():
    names={c['name'] for c in sa.inspect(op.get_bind()).get_columns('resource_generation_tasks')}
    for name,kind in [('class_id',sa.Integer()),('retry_root_id',sa.String(64)),('request_body_hash',sa.String(64))]:
        if name not in names:op.add_column('resource_generation_tasks',sa.Column(name,kind,nullable=True))
    indexes={i['name'] for i in sa.inspect(op.get_bind()).get_indexes('resource_generation_tasks')}
    for name,columns in [('ix_resource_class_time',['class_id','created_at']),('ix_resource_retry_root',['retry_root_id'])]:
        if name not in indexes:op.create_index(name,'resource_generation_tasks',columns)


def downgrade():
    for name in ['ix_resource_class_time','ix_resource_retry_root']:op.drop_index(name,table_name='resource_generation_tasks')
    for name in ['request_body_hash','retry_root_id','class_id']:op.drop_column('resource_generation_tasks',name)
