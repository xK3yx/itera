"""v3.1 — llm_call_logs table, match_details on progress logs, version on knowledge_bases

Revision ID: e1f2a3b4c5d6
Revises: d9f7a5b03c41
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd9f7a5b03c41'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- llm_call_logs table ---
    op.create_table(
        'llm_call_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('call_type', sa.String(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('prompt_messages', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('raw_response', sa.Text(), nullable=False),
        sa.Column('parsed_successfully', sa.Boolean(), nullable=False),
        sa.Column('parse_attempts', sa.Integer(), server_default='1', nullable=True),
        sa.Column('tokens_input', sa.Integer(), nullable=True),
        sa.Column('tokens_output', sa.Integer(), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('hallucination_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('topic_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_llm_call_logs_roadmap_id', 'llm_call_logs', ['roadmap_id'])
    op.create_index('ix_llm_call_logs_call_type', 'llm_call_logs', ['call_type'])
    op.create_index('ix_llm_call_logs_created_at', 'llm_call_logs', ['created_at'])

    # --- match_details JSONB on topic_progress_logs ---
    op.add_column(
        'topic_progress_logs',
        sa.Column('match_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # --- version INTEGER on knowledge_bases ---
    op.add_column(
        'knowledge_bases',
        sa.Column('version', sa.Integer(), server_default='1', nullable=True),
    )


def downgrade() -> None:
    op.drop_column('knowledge_bases', 'version')
    op.drop_column('topic_progress_logs', 'match_details')
    op.drop_index('ix_llm_call_logs_created_at', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_call_type', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_roadmap_id', table_name='llm_call_logs')
    op.drop_table('llm_call_logs')
