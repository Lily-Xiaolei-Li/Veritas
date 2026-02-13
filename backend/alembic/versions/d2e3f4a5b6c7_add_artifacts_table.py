"""add_artifacts_table

Revision ID: d2e3f4a5b6c7
Revises: c1b2f3e4d5a6
Create Date: 2026-01-25 16:00:00.000000

B1.3 - Artifact Handling
- artifacts: Agent-generated output files with FK to runs/sessions
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1b2f3e4d5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('storage_path', sa.String(1024), nullable=False),
        sa.Column('extension', sa.String(32), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('artifact_type', sa.String(50), nullable=False, server_default='file'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('artifact_meta', sa.JSON(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Create composite indexes for fast queries
    op.create_index('ix_artifacts_session_created', 'artifacts', ['session_id', 'created_at'])
    op.create_index('ix_artifacts_run_created', 'artifacts', ['run_id', 'created_at'])
    op.create_index('ix_artifacts_artifact_type', 'artifacts', ['artifact_type'])
    op.create_index('ix_artifacts_extension', 'artifacts', ['extension'])
    op.create_index('ix_artifacts_is_deleted', 'artifacts', ['is_deleted'])


def downgrade() -> None:
    # Drop artifacts table (indexes dropped automatically)
    op.drop_table('artifacts')
