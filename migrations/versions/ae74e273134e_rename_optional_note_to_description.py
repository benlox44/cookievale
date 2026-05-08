"""rename optional_note to description

Revision ID: ae74e273134e
Revises: b9c5921e9b16
Create Date: 2026-05-08 22:15:35.282297

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ae74e273134e"
down_revision: Union[str, None] = "b9c5921e9b16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("orders", "optional_note", new_column_name="description")
    op.execute(
        "UPDATE orders SET description = 'Sin descripción' WHERE description IS NULL"
    )
    op.alter_column("orders", "description", nullable=False)


def downgrade() -> None:
    op.alter_column("orders", "description", nullable=True)
    op.alter_column("orders", "description", new_column_name="optional_note")
