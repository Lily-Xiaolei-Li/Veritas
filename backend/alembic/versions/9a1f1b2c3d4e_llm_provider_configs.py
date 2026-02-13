"""llm provider configs

Revision ID: 9a1f1b2c3d4e
Revises: c2fd0c7f18a9
Create Date: 2026-02-11

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9a1f1b2c3d4e"
down_revision = "c2fd0c7f18a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_provider_configs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("config_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_llm_provider_configs_provider",
        "llm_provider_configs",
        ["provider"],
        unique=True,
    )
    op.create_index(
        "ix_llm_provider_configs_updated_at",
        "llm_provider_configs",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_llm_provider_configs_updated_at", table_name="llm_provider_configs")
    op.drop_index("ix_llm_provider_configs_provider", table_name="llm_provider_configs")
    op.drop_table("llm_provider_configs")
