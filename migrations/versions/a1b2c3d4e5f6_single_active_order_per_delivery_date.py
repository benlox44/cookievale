"""Enforce a single active order per delivery date.

Revision ID: a1b2c3d4e5f6
Revises: 0e8f2a1b3c4d
Create Date: 2026-08-16

A partial unique index on the delivery date (excluding rejected orders) turns
the check-then-insert race in order creation into a database error, so two
orders can never book the same delivery slot at the same time.
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "0e8f2a1b3c4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_orders_delivery_date_active",
        "orders",
        [sa.text("date(delivery_date)")],
        unique=True,
        postgresql_where=sa.text("status <> 'REJECTED'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_orders_delivery_date_active",
        table_name="orders",
        postgresql_where=sa.text("status <> 'REJECTED'"),
    )
