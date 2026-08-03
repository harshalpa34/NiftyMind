"""create_stock_prices_table

Revision ID: ece3bba1c3d5
Revises: e86703fdcb91
Create Date: 2026-07-26 03:44:40.956303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ece3bba1c3d5'
down_revision: Union[str, Sequence[str], None] = 'e86703fdcb91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE stock_prices (
            symbol VARCHAR(50) PRIMARY KEY,
            price NUMERIC(18, 4) NOT NULL CHECK (price >= 0),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS stock_prices")
