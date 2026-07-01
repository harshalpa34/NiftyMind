import pytest
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime, timezone, timedelta
import uuid

from app.db.crud.portfolio import (
    create_portfolio,
    upsert_holding,
    save_stock_news,
    save_news_analysis,
    upsert_holding_suggestion,
    get_holding_suggestions,
    get_news_for_holdings
)

# Sample Google News RSS item string
SAMPLE_RSS_XML = """
<rss version="2.0">
  <channel>
    <title>Google News search results</title>
    <item>
      <title>Tata Motors EV sales drop 18 percent in Q3 - Economic Times</title>
      <link>https://economictimes.indiatimes.com/news/ev-sales-drop</link>
      <pubDate>Fri, 26 Jun 2026 12:00:00 GMT</pubDate>
      <source url="https://economictimes.indiatimes.com">Economic Times</source>
    </item>
  </channel>
</rss>
"""

@pytest.mark.anyio
async def test_rss_xml_parsing():
    """Verify standard XML feed parsing returns expected fields."""
    root = ET.fromstring(SAMPLE_RSS_XML)
    items = root.find("channel").findall("item")
    
    assert len(items) == 1
    item = items[0]
    
    title = item.find("title").text
    link = item.find("link").text
    pub_date_str = item.find("pubDate").text
    source = item.find("source").text
    
    assert "Tata Motors EV sales drop" in title
    assert link == "https://economictimes.indiatimes.com/news/ev-sales-drop"
    assert source == "Economic Times"
    
    # Check pubDate parsing
    pub_date = email.utils.parsedate_to_datetime(pub_date_str)
    assert pub_date.year == 2026
    assert pub_date.month == 6


@pytest.mark.anyio
async def test_db_news_and_suggestions_queries(db_conn):
    """Verify crud methods for saving news, analyses, and suggestions work properly."""
    # Create test user conforming to conftest clean_database prefix (testuser_%)
    user_id = uuid.uuid4()
    await db_conn.execute(
        "INSERT INTO users (id, email, hashed_password) VALUES ($1, $2, $3)",
        user_id, f"testuser_watchdog_{uuid.uuid4().hex[:8]}@example.com", "mock_pass"
    )
    
    portfolio = await create_portfolio(db_conn, "Watchdog test portfolio", user_id)
    portfolio_id = portfolio["id"]
    
    symbol = "TATAMOTORS"
    holding = await upsert_holding(db_conn, portfolio_id, symbol, 10.0, 920.0)
    assert holding["symbol"] == symbol
    
    # 1. Save stock news
    pub_date = datetime.now(timezone.utc)
    news_record = await save_stock_news(
        conn=db_conn,
        symbol=symbol,
        title="Tata Motors EV Sales Miss",
        content="EV sales decline 18%",
        source="Economic Times",
        url="https://example.com/tata-ev-sales",
        published_at=pub_date
    )
    assert news_record["id"] is not None
    assert news_record["symbol"] == symbol
    
    # 2. Save news analysis
    analysis_record = await save_news_analysis(
        conn=db_conn,
        news_id=news_record["id"],
        symbol=symbol,
        sentiment="NEGATIVE",
        impact_level="HIGH",
        impact_type="PRICE_SENSITIVE",
        summary="EV volume decline signals near term margin pressure.",
        price_effect="This could put downward pressure on short term price"
    )
    assert analysis_record["id"] is not None
    assert analysis_record["sentiment"] == "NEGATIVE"
    
    # 3. Retrieve news and analysis for portfolio holdings
    recent_news = await get_news_for_holdings(db_conn, portfolio_id)
    assert len(recent_news) == 1
    assert recent_news[0]["sentiment"] == "NEGATIVE"
    assert recent_news[0]["symbol"] == symbol
    
    # 4. Upsert AI Suggestions and Target Prices
    q_targets = {
        "q1_target": 910.0,
        "q2_target": 940.0,
        "q3_target": 980.0,
        "q4_target": 1050.0,
        "target_rationale": "Strong recovery expected in Q3/Q4"
    }
    
    suggestion = await upsert_holding_suggestion(
        conn=db_conn,
        portfolio_id=portfolio_id,
        symbol=symbol,
        suggested_stop_loss=845.0,
        risk_signal="WATCH",
        reasoning="EV sales decline pressures near-term pricing.",
        quarterly_targets=q_targets
    )
    assert suggestion["id"] is not None
    assert suggestion["risk_signal"] == "WATCH"
    assert float(suggestion["suggested_stop_loss"]) == 845.0
    
    # 5. Retrieve suggestions
    retrieved = await get_holding_suggestions(db_conn, portfolio_id)
    assert len(retrieved) == 1
    assert retrieved[0]["symbol"] == symbol
    assert retrieved[0]["quarterly_targets"]["q1_target"] == 910.0
