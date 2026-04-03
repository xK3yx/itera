"""v3.2 — resource_cache table for reusing topic resources across roadmaps

Revision ID: f2g3h4i5j6k7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'f2g3h4i5j6k7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'resource_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('search_query', sa.Text(), nullable=False),
        sa.Column('resources', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('hit_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_resource_cache_search_query', 'resource_cache', ['search_query'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_resource_cache_search_query', table_name='resource_cache')
    op.drop_table('resource_cache')
