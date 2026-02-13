"""add_file_index_tables

Revision ID: c1b2f3e4d5a6
Revises: b8e953065f88
Create Date: 2026-01-25 14:00:00.000000

B1.2 - File Browser & Workspace
- file_index: Workspace file metadata for browsing
- session_file_attachments: Files attached to sessions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1b2f3e4d5a6'
down_revision: Union[str, None] = 'b8e953065f88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create file_index table
    op.create_table(
        'file_index',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('path', sa.String(1024), nullable=False, unique=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('extension', sa.String(32), nullable=True),
        sa.Column('parent_dir', sa.String(1024), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('hash_algo', sa.String(16), nullable=False, server_default='sha256'),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )

    # Create indexes for fast browsing
    op.create_index('ix_file_index_path', 'file_index', ['path'], unique=True)
    op.create_index('ix_file_index_parent_dir', 'file_index', ['parent_dir'])
    op.create_index('ix_file_index_extension', 'file_index', ['extension'])
    op.create_index('ix_file_index_is_deleted', 'file_index', ['is_deleted'])
    op.create_index('ix_file_index_modified_at', 'file_index', ['modified_at'])
    op.create_index('ix_file_index_content_hash', 'file_index', ['content_hash'])

    # Create session_file_attachments table
    op.create_table(
        'session_file_attachments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('file_id', sa.String(36), nullable=False),
        sa.Column('attached_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('ix_session_file_attachments_session_id', 'session_file_attachments', ['session_id'])
    op.create_index('ix_session_file_attachments_file_id', 'session_file_attachments', ['file_id'])
    op.create_index(
        'ix_session_file_attachments_unique',
        'session_file_attachments',
        ['session_id', 'file_id'],
        unique=True
    )


def downgrade() -> None:
    # Drop session_file_attachments table
    op.drop_table('session_file_attachments')

    # Drop file_index table
    op.drop_table('file_index')
