"""add_llm_usage_table

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-01-25 18:00:00.000000

B2.0 - LLM Provider Abstraction
- llm_usage: LLM API usage tracking for cost and observability
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create llm_usage table
    op.create_table(
        'llm_usage',
        sa.Column('id', sa.String(36), primary_key=True),
        # Context
        sa.Column('run_id', sa.String(36), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        # Provider/Model
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('request_type', sa.String(20), nullable=False, server_default='complete'),
        # Status
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_type', sa.String(50), nullable=True),
        # Token usage (nullable)
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('tokens_unavailable_reason', sa.String(100), nullable=True),
        # Cost in cents (nullable)
        sa.Column('input_cost_cents', sa.Integer(), nullable=True),
        sa.Column('output_cost_cents', sa.Integer(), nullable=True),
        sa.Column('total_cost_cents', sa.Integer(), nullable=True),
        sa.Column('cost_unavailable_reason', sa.String(100), nullable=True),
        # Performance (always available)
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('total_latency_ms', sa.Integer(), nullable=False),
        # Provider metadata
        sa.Column('provider_request_id', sa.String(100), nullable=True),
        sa.Column('finish_reason', sa.String(50), nullable=True),
        sa.Column('attempted_providers', sa.Text(), nullable=True),
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('ix_llm_usage_run_id', 'llm_usage', ['run_id'])
    op.create_index('ix_llm_usage_session_id', 'llm_usage', ['session_id'])
    op.create_index('ix_llm_usage_provider', 'llm_usage', ['provider'])
    op.create_index('ix_llm_usage_model', 'llm_usage', ['model'])
    op.create_index('ix_llm_usage_status', 'llm_usage', ['status'])
    op.create_index('ix_llm_usage_session_created', 'llm_usage', ['session_id', 'created_at'])
    op.create_index('ix_llm_usage_provider_created', 'llm_usage', ['provider', 'created_at'])


def downgrade() -> None:
    # Drop llm_usage table (indexes dropped automatically)
    op.drop_table('llm_usage')
