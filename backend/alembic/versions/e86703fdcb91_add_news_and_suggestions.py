"""add_news_and_suggestions

Revision ID: e86703fdcb91
Revises: 297e31d3a54f
Create Date: 2026-06-27 01:21:59.914323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e86703fdcb91'
down_revision: Union[str, Sequence[str], None] = '297e31d3a54f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create stock_news table
    op.execute("""
        CREATE TABLE stock_news (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            symbol VARCHAR(50) NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            source VARCHAR(255),
            url TEXT,
            published_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX ix_stock_news_symbol ON stock_news(symbol)")

    # Create news_analyses table
    op.execute("""
        CREATE TABLE news_analyses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            news_id UUID NOT NULL REFERENCES stock_news(id) ON DELETE CASCADE,
            symbol VARCHAR(50) NOT NULL,
            sentiment VARCHAR(20) NOT NULL,
            impact_level VARCHAR(20) NOT NULL,
            impact_type VARCHAR(50) NOT NULL,
            summary TEXT NOT NULL,
            price_effect TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX ix_news_analyses_symbol ON news_analyses(symbol)")

    # Create holding_suggestions table
    op.execute("""
        CREATE TABLE holding_suggestions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol VARCHAR(50) NOT NULL,
            suggested_stop_loss NUMERIC(18, 4),
            risk_signal VARCHAR(20) NOT NULL,
            reasoning TEXT,
            quarterly_targets JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_holding_suggestions_portfolio_symbol UNIQUE (portfolio_id, symbol)
        )
    """)
    op.execute("CREATE INDEX ix_holding_suggestions_portfolio_id ON holding_suggestions(portfolio_id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS holding_suggestions")
    op.execute("DROP TABLE IF EXISTS news_analyses")
    op.execute("DROP TABLE IF EXISTS stock_news")

