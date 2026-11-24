"""Add pg_trgm GIN index on orders.customer_instagram for fast autocomplete."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    op.create_index(
        "ix_orders_customer_instagram_trgm",
        "orders",
        ["customer_instagram"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"customer_instagram": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_orders_customer_instagram_trgm", table_name="orders")
