"""add rag_sources table

Revision ID: f4a6c7d8e9f0
Revises: e3f4a5b6c7d8
Create Date: 2026-02-10

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f4a6c7d8e9f0"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rag_sources",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preset", sa.String(length=50), nullable=False, server_default="generic"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="creating"),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_rag_sources_name", "rag_sources", ["name"], unique=True)
    op.create_index("ix_rag_sources_status", "rag_sources", ["status"], unique=False)


def downgrade():
    op.drop_index("ix_rag_sources_status", table_name="rag_sources")
    op.drop_index("ix_rag_sources_name", table_name="rag_sources")
    op.drop_table("rag_sources")
