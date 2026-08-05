from collections.abc import Sequence

from alembic import op

revision: str = "0e8f2a1b3c4d"
down_revision: str | None = "2fbdc090e784"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE orders SET customer_instagram = lower(customer_instagram)")


def downgrade() -> None:
    # Data change is not reversible: we cannot reconstruct the original casing.
    pass
