"""Freeze formal tutoring scope; never infer historical class membership."""
from alembic import op
import sqlalchemy as sa

revision = '20261018_0034'
down_revision = '20261018_0033'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c['name'] for c in inspector.get_columns('tutor_sessions')}
    for name, column_type in (('class_id', sa.Integer()), ('formal_question_id', sa.Integer()),
                              ('concept_id', sa.String(80))):
        if name not in columns:
            op.add_column('tutor_sessions', sa.Column(name, column_type, nullable=True))
    if 'ix_tutor_session_class_time' not in {i['name'] for i in inspector.get_indexes('tutor_sessions')}:
        op.create_index('ix_tutor_session_class_time', 'tutor_sessions', ['class_id', 'created_at'])


def downgrade():
    op.drop_index('ix_tutor_session_class_time', table_name='tutor_sessions')
    for name in ('concept_id', 'formal_question_id', 'class_id'):
        op.drop_column('tutor_sessions', name)
