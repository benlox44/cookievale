from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
revision: str = '9734f1f0f42e'
down_revision: Union[str, None] = '7b6efd74dbec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('products', sa.Column('display_order', sa.Integer(), server_default='0', nullable=False))

def downgrade() -> None:
    op.drop_column('products', 'display_order')
