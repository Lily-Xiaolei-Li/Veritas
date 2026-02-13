"""add_future_proofing_and_auth_tables

Revision ID: 0881425e5f56
Revises: ccf5b0120261
Create Date: 2026-01-24 10:18:38.853842

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0881425e5f56'
down_revision: Union[str, None] = 'ccf5b0120261'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Future-proofing: Add circle_id and rationale to events table
    op.add_column('events', sa.Column('circle_id', sa.String(50), nullable=True))
    op.add_column('events', sa.Column('rationale', sa.Text(), nullable=True))
    op.create_index('ix_events_circle_id', 'events', ['circle_id'])

    # Future-proofing: Add circle_id and rationale to audit_log table
    op.add_column('audit_log', sa.Column('circle_id', sa.String(50), nullable=True))
    op.add_column('audit_log', sa.Column('rationale', sa.Text(), nullable=True))
    op.create_index('ix_audit_log_circle_id', 'audit_log', ['circle_id'])

    # Future-proofing: Create state_snapshots table for LangGraph persistence
    op.create_table(
        'state_snapshots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('checkpoint_id', sa.String(255), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('state_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_state_snapshots_run_id', 'state_snapshots', ['run_id'])
    op.create_index('ix_state_snapshots_checkpoint_id', 'state_snapshots', ['checkpoint_id'])
    op.create_index('ix_state_snapshots_created_at', 'state_snapshots', ['created_at'])

    # Authentication: Create users table for password authentication
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    # Authentication: Create api_keys table for encrypted API key storage
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('encrypted_key', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index('ix_api_keys_provider', 'api_keys', ['provider'])
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])
    op.create_index('ix_api_keys_created_at', 'api_keys', ['created_at'])


def downgrade() -> None:
    # Drop api_keys table
    op.drop_table('api_keys')

    # Drop users table
    op.drop_table('users')

    # Drop state_snapshots table
    op.drop_table('state_snapshots')

    # Remove circle_id and rationale from audit_log
    op.drop_index('ix_audit_log_circle_id', 'audit_log')
    op.drop_column('audit_log', 'rationale')
    op.drop_column('audit_log', 'circle_id')

    # Remove circle_id and rationale from events
    op.drop_index('ix_events_circle_id', 'events')
    op.drop_column('events', 'rationale')
    op.drop_column('events', 'circle_id')
