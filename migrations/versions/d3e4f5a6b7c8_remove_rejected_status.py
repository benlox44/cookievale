"""Remove the rejected order status and drop its slot-freeing logic."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rejection no longer exists: freeing a slot means deleting the order, so
    # purge any previously rejected rows (and their line items) first.
    op.execute(
        sa.text(
            "DELETE FROM order_items "
            "WHERE order_id IN (SELECT id FROM orders WHERE status = 'REJECTED')"
        )
    )
    op.execute(sa.text("DELETE FROM orders WHERE status = 'REJECTED'"))

    # A slot can now be held by exactly one order, so the partial unique index
    # (which excluded rejected orders) becomes a plain unique index.
    op.drop_index("uq_orders_availability_slot_active", table_name="orders")

    op.execute(sa.text("ALTER TYPE orderstatus RENAME TO orderstatus_old"))
    op.execute(
        sa.text(
            "CREATE TYPE orderstatus AS ENUM "
            "('PENDING', 'CONFIRMED', 'PAID', 'DELIVERED')"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE orders ALTER COLUMN status "
            "TYPE orderstatus USING status::text::orderstatus"
        )
    )
    op.execute(sa.text("DROP TYPE orderstatus_old"))

    op.create_index(
        "uq_orders_availability_slot_active",
        "orders",
        ["availability_slot_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_orders_availability_slot_active", table_name="orders")

    op.execute(sa.text("ALTER TYPE orderstatus RENAME TO orderstatus_old"))
    op.execute(
        sa.text(
            "CREATE TYPE orderstatus AS ENUM "
            "('PENDING', 'CONFIRMED', 'PAID', 'DELIVERED', 'REJECTED')"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE orders ALTER COLUMN status "
            "TYPE orderstatus USING status::text::orderstatus"
        )
    )
    op.execute(sa.text("DROP TYPE orderstatus_old"))

    op.create_index(
        "uq_orders_availability_slot_active",
        "orders",
        ["availability_slot_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'REJECTED'"),
    )
