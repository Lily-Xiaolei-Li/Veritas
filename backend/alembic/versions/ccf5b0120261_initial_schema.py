"""initial_schema

Revision ID: ccf5b0120261
Revises: 
Create Date: 2026-01-23 23:11:38.092548

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ccf5b0120261'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('mode', sa.String(50), nullable=False, server_default='engineering'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('config', sa.JSON(), nullable=True),
    )
    op.create_index('ix_sessions_created_at', 'sessions', ['created_at'])
    op.create_index('ix_sessions_status', 'sessions', ['status'])

    # Create runs table
    op.create_table(
        'runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('task', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('brain_used', sa.String(50), nullable=True),
        sa.Column('run_metadata', sa.JSON(), nullable=True),
    )
    op.create_index('ix_runs_session_id', 'runs', ['session_id'])
    op.create_index('ix_runs_created_at', 'runs', ['created_at'])
    op.create_index('ix_runs_status', 'runs', ['status'])
    op.create_index('ix_runs_escalated', 'runs', ['escalated'])

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('component', sa.String(100), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False, server_default='info'),
    )
    op.create_index('ix_events_run_id', 'events', ['run_id'])
    op.create_index('ix_events_session_id', 'events', ['session_id'])
    op.create_index('ix_events_created_at', 'events', ['created_at'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_severity', 'events', ['severity'])

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actor', sa.String(100), nullable=False),
        sa.Column('actor_id', sa.String(100), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(255), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_actor', 'audit_log', ['actor'])
    op.create_index('ix_audit_log_session_id', 'audit_log', ['session_id'])


def downgrade() -> None:
    # Drop tables in reverse order (audit_log, events, runs, sessions)
    op.drop_table('audit_log')
    op.drop_table('events')
    op.drop_table('runs')
    op.drop_table('sessions')
