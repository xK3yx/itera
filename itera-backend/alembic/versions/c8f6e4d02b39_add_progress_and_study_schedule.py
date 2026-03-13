"""add progress tracking and study schedule

Revision ID: c8f6e4d02b39
Revises: b7e5f3c91a28
Create Date: 2026-03-13 00:00:00.000000

"""
from typing import Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'c8f6e4d02b39'
down_revision: Union[str, None] = 'b7e5f3c91a28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Feature 2: completed_topics on roadmaps
    op.add_column(
        'roadmaps',
        sa.Column('completed_topics', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # Feature 3: study_schedules table
    op.create_table(
        'study_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'session_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('sessions.id', ondelete='CASCADE'),
            nullable=False,
            unique=True
        ),
        sa.Column('daily_hours', sa.Float(), nullable=False),
        sa.Column('study_days', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('schedule', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('study_schedules')
    op.drop_column('roadmaps', 'completed_topics')
