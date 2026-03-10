"""add weekly_hours and estimated_weeks to roadmaps

Revision ID: b7e5f3c91a28
Revises: a6dda4a72cc2
Create Date: 2026-03-10 06:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7e5f3c91a28'
down_revision: Union[str, None] = 'a6dda4a72cc2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('roadmaps', sa.Column('weekly_hours', sa.Integer(), nullable=True))
    op.add_column('roadmaps', sa.Column('estimated_weeks', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('roadmaps', 'estimated_weeks')
    op.drop_column('roadmaps', 'weekly_hours')
