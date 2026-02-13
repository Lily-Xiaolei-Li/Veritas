"""personas sort_order

Revision ID: c2fd0c7f18a9
Revises: 7b9c3d2a1f1a
Create Date: 2026-02-11

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2fd0c7f18a9"
down_revision = "7b9c3d2a1f1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "personas",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index("ix_personas_sort_order", "personas", ["sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_personas_sort_order", table_name="personas")
    op.drop_column("personas", "sort_order")
