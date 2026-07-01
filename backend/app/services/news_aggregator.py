import logging
import asyncio
import xml.etree.ElementTree as ET
import email.utils
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import httpx
from langchain_core.documents import Document

from app.db.session import pg_pool
from app.db.crud.portfolio import (
    save_stock_news,
    save_news_analysis,
    upsert_holding_suggestion,
    get_news_for_holdings
)
from app.services.portfolio_risk import portfolio_risk_service
from app.services.news_sentiment_service import news_sentiment_service
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)

class NewsAggregatorService:
    async def sync_portfolio_and_generate_suggestions(
        self,
        conn,
        portfolio_id: uuid.UUID,
        holdings: List[Dict[str, Any]],
        force_refresh: bool = False
    ) -> None:
        """
        On-demand atomic sync for a specific portfolio:
        1. Fetches raw RSS news for each symbol (updates stock_news).
        2. Batches analysis for any unanalyzed news articles via Gemini.
        3. Checks if holding suggestions are missing or older than 30 minutes.
        4. Batches generation of stop losses, risk ratings, and targets via Gemini if needed.
        """
        if not holdings:
            return

        logger.info(f"[Watchdog] Starting on-demand news sync for portfolio={portfolio_id}")

        # 1. Fetch latest raw RSS news for all holdings sequentially
        async with httpx.AsyncClient() as client:
            for h in holdings:
                symbol = h["symbol"].upper()
                try:
                    await self.aggregate_symbol_news(conn, client, symbol)
                except Exception as e:
                    logger.error(f"[Watchdog] Failed raw news aggregation for {symbol}: {e}")

        # 2. Batch-analyze any unanalyzed news articles in the last 24 hours
        # Fetch articles for portfolio symbols that do NOT have matching news_analyses row
        unanalyzed_query = """
            SELECT sn.id, sn.symbol, sn.title, sn.url, sn.source, sn.published_at
            FROM stock_news sn
            JOIN holdings h ON UPPER(sn.symbol) = UPPER(h.symbol)
            LEFT JOIN news_analyses na ON sn.id = na.news_id
            WHERE h.portfolio_id = $1 
              AND sn.published_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
              AND na.sentiment IS NULL
        """
        rows = await conn.fetch(unanalyzed_query, portfolio_id)
        unanalyzed_articles = [dict(r) for r in rows]

        if unanalyzed_articles:
            logger.info(f"[Watchdog] Found {len(unanalyzed_articles)} unanalyzed news articles. Triggering batched analysis...")
            # Prepare batch input
            batch_inputs = [
                {"id": str(art["id"]), "symbol": art["symbol"], "title": art["title"]}
                for art in unanalyzed_articles
            ]
            
            # Send to Gemini in a single batch call
            batch_results = await news_sentiment_service.analyze_articles_batch(batch_inputs)
            
            # Map by ID for quick lookup
            articles_map = {str(a["id"]): a for a in unanalyzed_articles}
            docs_to_ingest = []
            
            # Save analyses to DB and build Pinecone docs
            for result in batch_results:
                news_id_str = result.get("id")
                art = articles_map.get(news_id_str)
                if not art:
                    continue
                
                try:
                    # Save to news_analyses DB
                    await save_news_analysis(
                        conn=conn,
                        news_id=uuid.UUID(news_id_str),
                        symbol=art["symbol"],
                        sentiment=result.get("sentiment", "NEUTRAL"),
                        impact_level=result.get("impact_level", "LOW"),
                        impact_type=result.get("impact_type", "PRICE_SENSITIVE"),
                        summary=result.get("summary", ""),
                        price_effect=result.get("price_effect", "")
                    )
                    
                    # Prepare Pinecone document
                    doc = Document(
                        page_content=f"Company: {art['symbol']} | Headline: {art['title']} | AI Summary: {result.get('summary')}",
                        metadata={
                            "company": art["symbol"],
                            "title": art["title"],
                            "url": art["url"],
                            "source": art["source"],
                            "published_at": str(art["published_at"]),
                            "doc_type": "news",
                            "sentiment": result.get("sentiment"),
                            "impact": result.get("impact_level")
                        }
                    )
                    docs_to_ingest.append(doc)
                except Exception as e:
                    logger.error(f"[Watchdog] Failed to save news analysis for {news_id_str}: {e}")

            # Ingest all new summaries into Pinecone in one batch
            if docs_to_ingest:
                try:
                    vector_store.ingest(docs_to_ingest, namespace="earnings")
                    logger.info(f"[Watchdog] Ingested {len(docs_to_ingest)} news summaries into Pinecone RAG")
                except Exception as ve:
                    logger.warning(f"[Watchdog] Failed to ingest news vector to Pinecone: {ve}")

        # 3. Check Suggestions Staleness
        # Fetch current suggestions to evaluate staleness
        sugg_query = "SELECT symbol, updated_at FROM holding_suggestions WHERE portfolio_id = $1"
        sugg_rows = await conn.fetch(sugg_query, portfolio_id)
        suggestions_db = {r["symbol"].upper(): r["updated_at"] for r in sugg_rows}

        needs_suggestions_refresh = force_refresh
        
        # Check if suggestions are missing or older than 30 minutes
        now_utc = datetime.now(timezone.utc)
        for h in holdings:
            symbol = h["symbol"].upper()
            updated_at = suggestions_db.get(symbol)
            if not updated_at:
                needs_suggestions_refresh = True
                logger.info(f"[Watchdog] Suggestion for {symbol} is missing. Triggering suggestions refresh.")
                break
            
            # Make updated_at timezone-aware to match now_utc
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            
            if now_utc - updated_at > timedelta(minutes=30):
                needs_suggestions_refresh = True
                logger.info(f"[Watchdog] Suggestion for {symbol} is stale ({now_utc - updated_at} old). Triggering suggestions refresh.")
                break

        # 4. Batch-generate holding recommendations via Gemini
        if needs_suggestions_refresh:
            logger.info(f"[Watchdog] Hitting Gemini to generate batch suggestions for all holdings...")
            
            # Fetch recent news for context
            recent_news = await get_news_for_holdings(conn, portfolio_id, limit_per_stock=5)
            news_by_symbol = {}
            for n in recent_news:
                sym = n["symbol"].upper()
                if sym not in news_by_symbol:
                    news_by_symbol[sym] = []
                news_by_symbol[sym].append(n)

            # Map holdings to standard format with current market price
            holdings_input = []
            for h in holdings:
                sym = h["symbol"].upper()
                avg_buy_price = float(h["average_buy_price"])
                current_price = portfolio_risk_service.get_current_price(sym, avg_buy_price)
                holdings_input.append({
                    "symbol": sym,
                    "average_buy_price": avg_buy_price,
                    "current_price": current_price
                })

            # Call Gemini suggestions batch API
            suggestions_ai = await news_sentiment_service.generate_holding_suggestions_batch(
                holdings=holdings_input,
                news_by_symbol=news_by_symbol
            )

            # Upsert results to holding_suggestions
            for sugg in suggestions_ai:
                sym = sugg["symbol"].upper()
                q_targets = {
                    "q1_target": sugg.get("q1_target"),
                    "q2_target": sugg.get("q2_target"),
                    "q3_target": sugg.get("q3_target"),
                    "q4_target": sugg.get("q4_target"),
                    "target_rationale": sugg.get("target_rationale")
                }
                
                try:
                    await upsert_holding_suggestion(
                        conn=conn,
                        portfolio_id=portfolio_id,
                        symbol=sym,
                        suggested_stop_loss=sugg.get("suggested_stop_loss"),
                        risk_signal=sugg.get("risk_signal") or "HOLD",
                        reasoning=sugg.get("reasoning"),
                        quarterly_targets=q_targets
                    )
                    logger.info(f"[Watchdog] Saved suggestion for {sym}: SL={sugg.get('suggested_stop_loss')} | Signal={sugg.get('risk_signal')}")
                except Exception as e:
                    logger.error(f"[Watchdog] Failed to save suggestions for {sym}: {e}")

            logger.info("[Watchdog] Batch suggestion update complete.")
        else:
            logger.info("[Watchdog] Suggestions are fresh (<30 min old). Skipping Gemini suggestions generation.")

    async def aggregate_symbol_news(self, conn, client: httpx.AsyncClient, symbol: str) -> None:
        """
        Fetches Google News RSS for a symbol, saves raw articles to stock_news.
        Does NOT trigger Gemini analysis — this is handled by the batched endpoint call.
        """
        logger.info(f"[Aggregator] Fetching RSS news feed for {symbol}")
        # Search query for Google News
        query = f"{symbol}+stock+market+India+NSE"
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = await client.get(url, headers=headers, timeout=15.0)
        if response.status_code != 200:
            logger.error(f"[Aggregator] Failed to fetch RSS feed for {symbol}: HTTP {response.status_code}")
            return
            
        # Parse XML
        root = ET.fromstring(response.content)
        items = root.find("channel").findall("item")
        
        logger.info(f"[Aggregator] {symbol}: RSS returned {len(items)} total items, processing top 15")
        
        now = datetime.now(timezone.utc)
        count = 0
        skipped_old = 0
        skipped_dup = 0
        
        # Process top 15 items
        for item in items[:15]:
            try:
                title = item.find("title").text
                link = item.find("link").text
                pub_date_str = item.find("pubDate").text
                source_el = item.find("source")
                source = source_el.text if source_el is not None else "Google News"
                
                # Parse date
                pub_date = email.utils.parsedate_to_datetime(pub_date_str)
                age = now - pub_date
                
                # Only include news from the last 24 hours
                if age > timedelta(hours=24):
                    skipped_old += 1
                    continue
                    
                # Save news article to DB
                news_record = await save_stock_news(
                    conn=conn,
                    symbol=symbol,
                    title=title,
                    content="",
                    source=source,
                    url=link,
                    published_at=pub_date
                )
                
                news_id = news_record.get("id")
                if not news_id:
                    skipped_dup += 1
                    continue
                    
                count += 1
            except Exception as e:
                logger.error(f"[Aggregator] Error processing RSS item for {symbol}: {e}")
                
        logger.info(f"[Aggregator] {symbol}: DONE — saved={count}, skipped_old={skipped_old}, skipped_dup={skipped_dup}")

# Singleton instance
news_aggregator = NewsAggregatorService()
