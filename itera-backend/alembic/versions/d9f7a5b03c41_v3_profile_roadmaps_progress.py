"""v3 profile, roadmaps, and progress tables

Revision ID: d9f7a5b03c41
Revises: c8f6e4d02b39
Create Date: 2026-03-26 00:00:00.000000

"""
from typing import Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'd9f7a5b03c41'
down_revision: Union[str, None] = 'c8f6e4d02b39'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- v3 profile columns on users table ---
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('github_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('linkedin_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('education', sa.String(), nullable=True))
    op.add_column('users', sa.Column('current_role', sa.String(), nullable=True))
    op.add_column('users', sa.Column('primary_domain', sa.String(), server_default='general', nullable=True))
    op.add_column('users', sa.Column('experience_years', sa.Integer(), server_default='0', nullable=True))
    op.add_column('users', sa.Column('tech_stack', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('users', sa.Column('profile_completed', sa.Boolean(), server_default=sa.text('false'), nullable=True))

    # --- generated_roadmaps table ---
    op.create_table(
        'generated_roadmaps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_role', sa.String(), nullable=False),
        sa.Column('learning_goal', sa.Text(), nullable=False),
        sa.Column('interests', sa.Text(), nullable=True),
        sa.Column('hours_per_week', sa.Float(), nullable=True),
        sa.Column('include_paid', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('total_estimated_hours', sa.Float(), server_default='0', nullable=True),
        sa.Column('roadmap_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )

    # --- knowledge_bases table ---
    op.create_table(
        'knowledge_bases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )

    # --- roadmap_enrollments table ---
    op.create_table(
        'roadmap_enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('completed_topic_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )

    # --- topic_progress_logs table ---
    op.create_table(
        'topic_progress_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('enrollment_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('topic_id', sa.String(), nullable=False),
        sa.Column('log_text', sa.Text(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('rejection_reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('topic_progress_logs')
    op.drop_table('roadmap_enrollments')
    op.drop_table('knowledge_bases')
    op.drop_table('generated_roadmaps')

    op.drop_column('users', 'profile_completed')
    op.drop_column('users', 'tech_stack')
    op.drop_column('users', 'experience_years')
    op.drop_column('users', 'primary_domain')
    op.drop_column('users', 'current_role')
    op.drop_column('users', 'education')
    op.drop_column('users', 'linkedin_url')
    op.drop_column('users', 'github_url')
    op.drop_column('users', 'bio')
    op.drop_column('users', 'full_name')
