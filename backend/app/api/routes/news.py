import uuid
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
import asyncpg
import httpx
import asyncio

from app.auth.dependencies import CurrentUser
from app.db.session import get_raw_db, pg_pool
from app.db.crud.portfolio import (
    get_portfolio,
    get_holdings,
    get_news_for_holdings,
    get_holding_suggestions,
    get_portfolio_news_feed
)
from app.services.portfolio_risk import portfolio_risk_service
from app.services.news_aggregator import news_aggregator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios", tags=["Portfolio Health Watchdog"])

@router.get("/{portfolio_id}/health", status_code=status.HTTP_200_OK)
async def api_get_portfolio_health(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    force_refresh: bool = Query(default=False),
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """
    Returns the compiled news sentiment summary, AI stop-losses, quarterly price targets,
    and recent news headlines for all holdings in a user's delivery portfolio.
    """
    # 1. Verify portfolio ownership
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )

    # 2. Get active holdings
    holdings = await get_holdings(conn, portfolio_id)
    if not holdings:
        return {
            "portfolio_name": portfolio["name"],
            "holdings": [],
            "health_score": 100.0,
            "overall_sentiment": "NEUTRAL"
        }

    # 3. Trigger on-demand sync & suggestions refresh (batches news RSS, batch Gemini sentiment, and batch Gemini recommendations)
    await news_aggregator.sync_portfolio_and_generate_suggestions(
        conn=conn,
        portfolio_id=portfolio_id,
        holdings=holdings,
        force_refresh=force_refresh
    )

    # 4. Retrieve fresh news & AI suggestions from DB
    news_list = await get_news_for_holdings(conn, portfolio_id, limit_per_stock=5)
    suggestions = await get_holding_suggestions(conn, portfolio_id)
    suggestions_map = {s["symbol"].upper(): s for s in suggestions}

    health_holdings = []
    neg_count = 0
    total_news = 0

    for h in holdings:
        symbol = h["symbol"].upper()
        qty = float(h["quantity"])
        avg_price = float(h["average_buy_price"])
        current_price = portfolio_risk_service.get_current_price(symbol, avg_price)

        # Filter news for this symbol
        stock_news = [n for n in news_list if n["symbol"].upper() == symbol]
        total_news += len(stock_news)

        pos_news = sum(1 for n in stock_news if n["sentiment"] == "POSITIVE")
        neg_news = sum(1 for n in stock_news if n["sentiment"] == "NEGATIVE")
        neut_news = sum(1 for n in stock_news if n["sentiment"] == "NEUTRAL")

        neg_count += neg_news

        latest_news = stock_news[0] if stock_news else None
        latest_headline = latest_news["title"] if latest_news else "No recent news"
        ai_summary = latest_news["ai_summary"] if latest_news and latest_news["ai_summary"] else "No recent developments detected."

        # Fetch suggestion — use `or` fallbacks because dict.get(key, default)
        # only returns the default when the key is ABSENT. If the DB value is NULL
        # the key exists with value None and the default is ignored.
        sugg = suggestions_map.get(symbol, {})
        suggested_stop_loss = sugg.get("suggested_stop_loss") or None
        risk_signal = sugg.get("risk_signal") or "HOLD"
        reasoning = sugg.get("reasoning") or "Hold position and watch for corporate updates."
        quarterly_targets = sugg.get("quarterly_targets")

        # Fallback quarterly targets if not computed yet
        if not quarterly_targets:
            quarterly_targets = {
                "q1_target": current_price * 1.03,
                "q2_target": current_price * 1.06,
                "q3_target": current_price * 1.09,
                "q4_target": current_price * 1.12,
                "target_rationale": "Moderate baseline targets in the absence of corporate transcript cues."
            }

        # Calculate dominant sentiment
        current_sentiment = "NEUTRAL"
        if pos_news > neg_news:
            current_sentiment = "POSITIVE"
        elif neg_news > pos_news:
            current_sentiment = "NEGATIVE"

        health_holdings.append({
            "symbol": symbol,
            "qty": qty,
            "avg_price": avg_price,
            "current_price": current_price,
            "current_sentiment": current_sentiment,
            "news_count_24h": len(stock_news),
            "positive_news": pos_news,
            "negative_news": neg_news,
            "neutral_news": neut_news,
            "latest_headline": latest_headline,
            "ai_summary": ai_summary,
            "suggested_stop_loss": suggested_stop_loss,
            "risk_signal": risk_signal,
            "reasoning": reasoning,
            "quarterly_targets": quarterly_targets,
            "top_news": [
                {
                    "title": n["title"],
                    "source": n["source"],
                    "url": n["url"],
                    "published_at": n["published_at"].isoformat() if n["published_at"] else None,
                    "sentiment": n["sentiment"],
                    "impact_level": n["impact_level"],
                    "impact_type": n["impact_type"],
                    "ai_summary": n["ai_summary"],
                    "price_effect": n["price_effect"]
                }
                for n in stock_news
            ]
        })

    # Overall portfolio sentiment
    overall_sentiment = "NEUTRAL"
    pos_total = sum(h["positive_news"] for h in health_holdings)
    neg_total = sum(h["negative_news"] for h in health_holdings)
    if pos_total > neg_total:
        overall_sentiment = "POSITIVE"
    elif neg_total > pos_total:
        overall_sentiment = "NEGATIVE"

    # Health score decreases as negative news count increases
    health_score = max(0.0, min(100.0, 100.0 - (neg_count * 10.0)))

    return {
        "portfolio_name": portfolio["name"],
        "health_score": round(health_score, 1),
        "overall_sentiment": overall_sentiment,
        "holdings": health_holdings
    }


@router.get("/{portfolio_id}/danger-zone", status_code=status.HTTP_200_OK)
async def api_get_danger_zone(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    conn: asyncpg.Connection = Depends(get_raw_db)
):
    """
    Proactively checks for critical negative triggers on portfolio holdings:
    - 2+ High-impact negative news articles in 24 hours.
    - Risk Signal evaluated as 'CAUTION' or 'EXIT'.
    - Price drop > 15% below buy price combined with negative news.
    """
    portfolio = await get_portfolio(conn, portfolio_id, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or access denied."
        )

    holdings = await get_holdings(conn, portfolio_id)
    if not holdings:
        return {
            "danger_stocks": [],
            "reasons": {},
            "recommended_action": "None"
        }

    news_list = await get_news_for_holdings(conn, portfolio_id, limit_per_stock=5)
    suggestions = await get_holding_suggestions(conn, portfolio_id)
    suggestions_map = {s["symbol"].upper(): s for s in suggestions}

    danger_stocks = []
    reasons = {}

    for h in holdings:
        symbol = h["symbol"].upper()
        avg_price = float(h["average_buy_price"])
        current_price = portfolio_risk_service.get_current_price(symbol, avg_price)
        
        stock_news = [n for n in news_list if n["symbol"].upper() == symbol]
        high_neg_news = [n for n in stock_news if n["sentiment"] == "NEGATIVE" and n["impact_level"] == "HIGH"]
        
        sugg = suggestions_map.get(symbol, {})
        risk_signal = sugg.get("risk_signal", "HOLD")

        is_danger = False
        danger_reason = []

        if len(high_neg_news) >= 2:
            is_danger = True
            danger_reason.append(f"Detected {len(high_neg_news)} high-impact negative news items in the last 24h.")

        if risk_signal in ("CAUTION", "EXIT"):
            is_danger = True
            danger_reason.append(f"AI Risk Watchdog raised '{risk_signal}' flag.")

        # Price dropped 15% below buy price
        if current_price < avg_price * 0.85:
            any_neg_news = any(n["sentiment"] == "NEGATIVE" for n in stock_news)
            if any_neg_news:
                is_danger = True
                danger_reason.append(f"Current price (₹{current_price}) is >15% below buy cost (₹{avg_price}) with active negative sentiment.")

        if is_danger:
            danger_stocks.append(symbol)
            reasons[symbol] = " & ".join(danger_reason)

    recommended_action = "None"
    if danger_stocks:
        recommended_action = "Review suggested stop loss, check latest headlines, and tighten capital protection."

    return {
        "danger_stocks": danger_stocks,
        "reasons": reasons,
        "recommended_action": recommended_action
    }


@router.get("/{portfolio_id}/news-feed", status_code=status.HTTP_200_OK)
async def api_get_portfolio_news_feed(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sentiment: Optional[str] = Query(default=None),
    force_refresh: bool = Query(default=False),
    conn: asyncpg.Connection = Depends(get_raw_db)
):

    # 2. Retrieve active symbols for holdings
    holdings = await get_holdings(conn, portfolio_id)
    logger.info(f"[NewsFeed] portfolio_id={portfolio_id} | holdings_count={len(holdings)} | symbols={[h['symbol'] for h in holdings]}")
    
    # 3. Trigger on-demand sync & suggestions refresh
    if holdings:
        await news_aggregator.sync_portfolio_and_generate_suggestions(
            conn=conn,
            portfolio_id=portfolio_id,
            holdings=holdings,
            force_refresh=force_refresh
        )
            
    # 4. Query the latest aggregated news feed from DB
    news = await get_portfolio_news_feed(
        conn=conn,
        portfolio_id=portfolio_id,
        limit=limit,
        offset=offset,
        sentiment=sentiment
    )
    
    # 5. Format results
    formatted_news = []
    for item in news:
        formatted_news.append({
            "news_id": str(item["news_id"]) if item["news_id"] else None,
            "symbol": item["symbol"],
            "title": item["title"],
            "content": item["content"],
            "source": item["source"],
            "url": item["url"],
            "published_at": item["published_at"].isoformat() if item["published_at"] else None,
            "analysis_id": str(item["analysis_id"]) if item["analysis_id"] else None,
            "sentiment": item["sentiment"] or "NEUTRAL",
            "impact_level": item["impact_level"] or "LOW",
            "impact_type": item["impact_type"] or "PRICE_SENSITIVE",
            "ai_summary": item["ai_summary"] or "No AI summary generated.",
            "price_effect": item["price_effect"]
        })
        
    return formatted_news

