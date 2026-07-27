from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9734f1f0f42e"
down_revision: str | None = "7b6efd74dbec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("products", "display_order")
