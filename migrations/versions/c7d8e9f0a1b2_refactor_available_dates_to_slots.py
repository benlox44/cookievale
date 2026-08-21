"""Replace unique available dates with reusable availability slots."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("uq_orders_delivery_date_active", table_name="orders")

    op.rename_table("available_dates", "availability_slots")
    op.drop_index("ix_available_dates_date", table_name="availability_slots")
    op.create_index(
        "ix_availability_slots_date", "availability_slots", ["date"], unique=False
    )
    op.execute(
        sa.text(
            """
            INSERT INTO availability_slots (date, created_at, updated_at)
            SELECT DISTINCT o.delivery_date::date, NOW(), NOW()
            FROM orders o
            WHERE NOT EXISTS (
                SELECT 1
                FROM availability_slots s
                WHERE s.date = o.delivery_date::date
            )
            """
        )
    )

    op.add_column(
        "orders",
        sa.Column("availability_slot_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE orders o
            SET availability_slot_id = s.id
            FROM availability_slots s
            WHERE s.date = o.delivery_date::date
            """
        )
    )
    op.create_foreign_key(
        "fk_orders_availability_slot_id",
        "orders",
        "availability_slots",
        ["availability_slot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_orders_availability_slot_active",
        "orders",
        ["availability_slot_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'REJECTED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_orders_availability_slot_active", table_name="orders")
    op.drop_constraint("fk_orders_availability_slot_id", "orders", type_="foreignkey")
    op.drop_column("orders", "availability_slot_id")
    op.drop_index("ix_availability_slots_date", table_name="availability_slots")
    op.create_index(
        "ix_available_dates_date", "availability_slots", ["date"], unique=True
    )
    op.rename_table("availability_slots", "available_dates")
    op.create_index(
        "uq_orders_delivery_date_active",
        "orders",
        [sa.text("date(delivery_date)")],
        unique=True,
        postgresql_where=sa.text("status <> 'REJECTED'"),
    )
