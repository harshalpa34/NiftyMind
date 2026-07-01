"""create_portfolio_tables

Revision ID: 297e31d3a54f
Revises: a1b2c3d4e5f6
Create Date: 2026-06-24 00:49:37.867367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '297e31d3a54f'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create portfolios table
    op.execute("""
        CREATE TABLE portfolios (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX ix_portfolios_user_id ON portfolios(user_id)")

    # Create holdings table
    op.execute("""
        CREATE TABLE holdings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol VARCHAR(50) NOT NULL,
            quantity NUMERIC(18, 4) NOT NULL CHECK (quantity >= 0),
            average_buy_price NUMERIC(18, 4) NOT NULL CHECK (average_buy_price >= 0),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_portfolio_symbol UNIQUE (portfolio_id, symbol)
        )
    """)
    op.execute("CREATE INDEX ix_holdings_portfolio_id ON holdings(portfolio_id)")

    # Create portfolio_transactions table
    op.execute("""
        CREATE TABLE portfolio_transactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol VARCHAR(50) NOT NULL,
            quantity NUMERIC(18, 4) NOT NULL CHECK (quantity > 0),
            price NUMERIC(18, 4) NOT NULL CHECK (price >= 0),
            transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX ix_portfolio_transactions_portfolio_id ON portfolio_transactions(portfolio_id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS portfolio_transactions")
    op.execute("DROP TABLE IF EXISTS holdings")
    op.execute("DROP TABLE IF EXISTS portfolios")
