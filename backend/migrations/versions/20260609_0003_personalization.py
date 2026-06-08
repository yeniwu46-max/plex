"""dynamic profiles and personalized resources

Revision ID: 20260609_0003
Revises: 20260530_0002
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = '20260609_0003'
down_revision = '20260530_0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'student_profiles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dimensions', sa.JSON(), nullable=False),
        sa.Column('completion_rate', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_student_profiles_user_id', 'student_profiles', ['user_id'])
    op.create_table(
        'student_profile_history',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('dimensions', sa.JSON(), nullable=False),
        sa.Column('changes', sa.JSON(), nullable=False),
        sa.Column('reason', sa.String(64), nullable=False),
        sa.Column('backend', sa.String(32), nullable=False),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_student_profile_history_user_id', 'student_profile_history', ['user_id'])
    op.create_table(
        'resource_generation_tasks',
        sa.Column('task_id', sa.String(64), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('knowledge_key', sa.String(32), nullable=False),
        sa.Column('requested_types', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('current_agent', sa.String(64)),
        sa.Column('steps', sa.JSON(), nullable=False),
        sa.Column('backend', sa.String(32), nullable=False),
        sa.Column('fallback_reason', sa.String(255)),
        sa.Column('error', sa.String(500)),
        sa.Column('retry_of', sa.String(64)),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('task_id'),
    )
    op.create_index('ix_resource_generation_tasks_task_id', 'resource_generation_tasks', ['task_id'])
    op.create_index('ix_resource_generation_tasks_user_id', 'resource_generation_tasks', ['user_id'])
    op.create_index('ix_resource_generation_tasks_knowledge_key', 'resource_generation_tasks', ['knowledge_key'])
    op.create_index('ix_resource_generation_tasks_status', 'resource_generation_tasks', ['status'])
    op.create_table(
        'personalized_learning_resources',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('generation_task_id', sa.String(64), sa.ForeignKey('resource_generation_tasks.task_id', ondelete='CASCADE'), nullable=False),
        sa.Column('knowledge_key', sa.String(32), nullable=False),
        sa.Column('knowledge_label', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(32), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('content_url', sa.String(500)),
        sa.Column('difficulty', sa.Integer(), nullable=False),
        sa.Column('estimated_minutes', sa.Integer(), nullable=False),
        sa.Column('profile_snapshot', sa.JSON(), nullable=False),
        sa.Column('recommendation_reason', sa.Text(), nullable=False),
        sa.Column('citations', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('review_status', sa.String(24), nullable=False),
        sa.Column('review_reason', sa.String(500)),
        sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('reviewed_at', sa.DateTime()),
        sa.Column('generator_agent', sa.String(64), nullable=False),
        sa.Column('backend', sa.String(32), nullable=False),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_personalized_learning_resources_user_id', 'personalized_learning_resources', ['user_id'])
    op.create_index('ix_personalized_learning_resources_generation_task_id', 'personalized_learning_resources', ['generation_task_id'])
    op.create_index('ix_personalized_learning_resources_knowledge_key', 'personalized_learning_resources', ['knowledge_key'])
    op.create_index('ix_personalized_learning_resources_resource_type', 'personalized_learning_resources', ['resource_type'])
    op.create_index('ix_personalized_learning_resources_review_status', 'personalized_learning_resources', ['review_status'])


def downgrade():
    op.drop_table('personalized_learning_resources')
    op.drop_table('resource_generation_tasks')
    op.drop_table('student_profile_history')
    op.drop_table('student_profiles')
