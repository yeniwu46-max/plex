"""Student arrival state, account appearance and transactional arrival counter."""
from alembic import op
import sqlalchemy as sa

revision = '20261014_0017'
down_revision = '20261014_0016'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = sa.inspect(bind).get_table_names()
    if 'student_onboarding' not in existing:
        op.create_table('student_onboarding',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('status', sa.String(16), nullable=False), sa.Column('survey_version', sa.Integer(), nullable=False),
            sa.Column('answers', sa.JSON(), nullable=False), sa.Column('draft', sa.JSON(), nullable=False),
            sa.Column('step', sa.Integer(), nullable=False), sa.Column('adventurer_number', sa.Integer(), unique=True),
            sa.Column('completed_at', sa.DateTime()), sa.Column('welcomed_at', sa.DateTime()))
    if 'adventurer_counter' not in existing:
        op.create_table('adventurer_counter', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('last_number', sa.Integer(), nullable=False))
    if 'user_appearance' not in existing:
        op.create_table('user_appearance', sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('visual_style', sa.String(10), nullable=False), sa.Column('color_mode', sa.String(10), nullable=False))
    metadata = sa.MetaData()
    arrival = sa.Table('student_onboarding', metadata, autoload_with=bind)
    counter = sa.Table('adventurer_counter', metadata, autoload_with=bind)
    users = sa.Table('users', metadata, autoload_with=bind)
    roles = sa.Table('roles', metadata, autoload_with=bind)
    if bind.execute(sa.select(counter.c.id).where(counter.c.id == 1)).first() is None:
        maximum = bind.execute(sa.select(sa.func.max(arrival.c.adventurer_number))).scalar()
        bind.execute(counter.insert().values(id=1, last_number=max(200, maximum or 200)))
    # Explicitly exempt historical users. Never overwrite pending/completed rows.
    ids = bind.execute(sa.select(users.c.id).join(roles, roles.c.id == users.c.role_id)
        .where(roles.c.name == 'student', ~sa.exists(sa.select(arrival.c.user_id).where(arrival.c.user_id == users.c.id)))).scalars()
    rows = [{'user_id': uid, 'status': 'exempt', 'survey_version': 1, 'answers': {}, 'draft': {}, 'step': 1} for uid in ids]
    if rows:
        bind.execute(arrival.insert(), rows)


def downgrade():
    for name in ('user_appearance', 'adventurer_counter', 'student_onboarding'):
        op.drop_table(name)
