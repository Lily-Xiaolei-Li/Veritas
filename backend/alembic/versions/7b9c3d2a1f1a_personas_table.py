"""personas table

Revision ID: 7b9c3d2a1f1a
Revises: 0a02cd5dd0c2
Create Date: 2026-02-11

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7b9c3d2a1f1a"
down_revision = "0a02cd5dd0c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personas",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.create_index("ix_personas_is_deleted", "personas", ["is_deleted"], unique=False)
    op.create_index("ix_personas_label", "personas", ["label"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_personas_label", table_name="personas")
    op.drop_index("ix_personas_is_deleted", table_name="personas")
    op.drop_table("personas")
