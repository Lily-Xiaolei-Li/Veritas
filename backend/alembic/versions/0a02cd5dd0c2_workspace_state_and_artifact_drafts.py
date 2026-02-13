"""workspace state and artifact drafts

Revision ID: 0a02cd5dd0c2
Revises: f4a6c7d8e9f0
Create Date: 2026-02-11 08:11:03.154807

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0a02cd5dd0c2'
down_revision: Union[str, None] = 'f4a6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sessions: workspace persistence
    op.add_column(
        "sessions",
        sa.Column(
            "workspace_state",
            sa.JSON(),
            nullable=False,
            server_default=text("'{}'::json"),
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "workspace_state_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "last_auto_save_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # artifacts: draft support (phase 1)
    op.add_column(
        "artifacts",
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default="upload",
        ),
    )
    op.add_column(
        "artifacts",
        sa.Column(
            "is_draft",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "artifacts",
        sa.Column(
            "draft_content",
            sa.Text(),
            nullable=True,
        ),
    )
    op.add_column(
        "artifacts",
        sa.Column(
            "draft_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("artifacts", "draft_updated_at")
    op.drop_column("artifacts", "draft_content")
    op.drop_column("artifacts", "is_draft")
    op.drop_column("artifacts", "source")

    op.drop_column("sessions", "last_auto_save_at")
    op.drop_column("sessions", "workspace_state_version")
    op.drop_column("sessions", "workspace_state")
