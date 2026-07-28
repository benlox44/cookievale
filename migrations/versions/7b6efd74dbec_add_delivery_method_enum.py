import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7b6efd74dbec"
down_revision: str | None = "fc50303b4ff8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    delivery_method_enum = postgresql.ENUM("PICKUP", "DELIVERY", name="deliverymethod")
    delivery_method_enum.create(op.get_bind())
    op.add_column(
        "orders",
        sa.Column(
            "delivery_method",
            delivery_method_enum,
            nullable=False,
            server_default="PICKUP",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "delivery_method")
    delivery_method_enum = postgresql.ENUM("PICKUP", "DELIVERY", name="deliverymethod")
    delivery_method_enum.drop(op.get_bind())
