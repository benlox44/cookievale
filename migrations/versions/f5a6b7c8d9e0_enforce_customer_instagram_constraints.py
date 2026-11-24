"""Enforce max length (30) and Instagram handle format CHECK on orders.customer_instagram."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHECK_NAME = "ck_orders_customer_instagram_format"
_CHECK_EXPR = (
    "customer_instagram ~ '^[a-z0-9_]([a-z0-9_.]{0,28}[a-z0-9_])?$' "
    "AND customer_instagram NOT LIKE '%..%'"
)


def upgrade() -> None:
    op.alter_column(
        "orders",
        "customer_instagram",
        existing_type=sa.String(),
        type_=sa.String(length=30),
        existing_nullable=False,
    )
    op.create_check_constraint(_CHECK_NAME, "orders", _CHECK_EXPR)


def downgrade() -> None:
    op.drop_constraint(_CHECK_NAME, "orders", type_="check")
    op.alter_column(
        "orders",
        "customer_instagram",
        existing_type=sa.String(length=30),
        type_=sa.String(),
        existing_nullable=False,
    )
