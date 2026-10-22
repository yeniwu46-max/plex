"""Owned practice, durable mock exams and seven-day resource trash."""
from alembic import op
import sqlalchemy as sa

revision = '20261022_0035'
down_revision = '20261018_0034'
branch_labels = depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if 'student_practice_attempts' not in tables:
        op.create_table('student_practice_attempts',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('question_ref', sa.String(100), nullable=False),
            sa.Column('question_version', sa.String(64), nullable=False),
            sa.Column('title', sa.String(200), nullable=False), sa.Column('code', sa.Text(), nullable=False),
            sa.Column('result', sa.JSON(), nullable=False), sa.Column('source', sa.String(32), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False))
        op.create_index('ix_student_practice_attempts_user_id', 'student_practice_attempts', ['user_id'])
        op.create_index('ix_student_practice_attempts_question_ref', 'student_practice_attempts', ['question_ref'])
    if 'student_question_favorites' not in tables:
        op.create_table('student_question_favorites',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
            sa.Column('question_ref', sa.String(100), primary_key=True),
            sa.Column('created_at', sa.DateTime(), nullable=False))
    if 'student_mock_exams' not in tables:
        op.create_table('student_mock_exams',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('active_user_id', sa.Integer(), unique=True),
            sa.Column('status', sa.String(24), nullable=False),
            sa.Column('questions', sa.JSON(), nullable=False), sa.Column('answers', sa.JSON(), nullable=False),
            sa.Column('results', sa.JSON(), nullable=False), sa.Column('revision', sa.Integer(), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=False), sa.Column('deadline', sa.DateTime(), nullable=False),
            sa.Column('submitted_at', sa.DateTime()), sa.Column('lease_until', sa.DateTime()), sa.Column('score', sa.Float()))
        op.create_index('ix_student_mock_exams_user_id', 'student_mock_exams', ['user_id'])
        op.create_index('ix_student_mock_exams_status', 'student_mock_exams', ['status'])
    columns = {c['name'] for c in inspector.get_columns('personalized_learning_resources')}
    for name, typ in [('deleted_at', sa.DateTime()), ('expires_at', sa.DateTime()), ('deletion_batch', sa.String(36)), ('purged_at', sa.DateTime())]:
        if name not in columns:
            op.add_column('personalized_learning_resources', sa.Column(name, typ))
            if name != 'purged_at':
                op.create_index('ix_personalized_learning_resources_' + name, 'personalized_learning_resources', [name])


def downgrade():
    for name in ('deleted_at', 'expires_at', 'deletion_batch', 'purged_at'):
        if name != 'purged_at':
            op.drop_index('ix_personalized_learning_resources_' + name, table_name='personalized_learning_resources')
        op.drop_column('personalized_learning_resources', name)
    for table in ('student_mock_exams', 'student_question_favorites', 'student_practice_attempts'):
        op.drop_table(table)
