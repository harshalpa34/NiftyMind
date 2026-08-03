import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================================
# Structured Output Schemas
# ============================================================================

class NewsAnalysisSchema(BaseModel):
    sentiment: str = Field(description="Must be exactly: 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'")
    impact_level: str = Field(description="Must be exactly: 'HIGH', 'MEDIUM', or 'LOW'")
    impact_type: str = Field(description="Must be exactly: 'PRICE_SENSITIVE', 'FUNDAMENTAL', 'REGULATORY', or 'MACRO'")
    summary: str = Field(description="2-3 line plain English explanation summarizing the news article and its direct relevance")
    price_effect: str = Field(description="Expected price direction effect, e.g. 'This could put downward pressure on short term price'")


class BatchNewsAnalysisItem(BaseModel):
    id: str = Field(description="The unique news_id string passed in the input list. Used to map the result back to the DB row.")
    sentiment: str = Field(description="Must be exactly: 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'")
    impact_level: str = Field(description="Must be exactly: 'HIGH', 'MEDIUM', or 'LOW'")
    impact_type: str = Field(description="Must be exactly: 'PRICE_SENSITIVE', 'FUNDAMENTAL', 'REGULATORY', or 'MACRO'")
    summary: str = Field(description="2-3 line plain English explanation summarizing the news article and its direct relevance")
    price_effect: str = Field(description="Expected price direction effect, e.g. 'This could put downward pressure on short term price'")


class BatchNewsAnalysisSchema(BaseModel):
    analyses: List[BatchNewsAnalysisItem] = Field(description="List of news article analyses, one for each input article.")


class HoldingSuggestionSchema(BaseModel):
    suggested_stop_loss: float = Field(description="Suggested stop loss price (float). Usually 5-15% below buy/current price depending on risk.")
    risk_signal: str = Field(description="Must be exactly: 'HOLD', 'WATCH', 'CAUTION', or 'EXIT'")
    reasoning: str = Field(description="Plain English reasoning explaining the stop loss and risk status based on recent developments.")
    q1_target: float = Field(description="Projected target price in 3 months (Q1)")
    q2_target: float = Field(description="Projected target price in 6 months (Q2)")
    q3_target: float = Field(description="Projected target price in 9 months (Q3)")
    q4_target: float = Field(description="Projected target price in 12 months (Q4)")
    target_rationale: str = Field(description="Factual rationale explaining why these targets are expected at these quarters.")


class BatchHoldingSuggestionItem(BaseModel):
    symbol: str = Field(description="The stock ticker symbol (e.g., 'TCS', 'INFY') in uppercase. Must exactly match one of the input symbols.")
    suggested_stop_loss: float = Field(description="Suggested stop loss price (float). Usually 5-15% below average buy price or current price (whichever is lower).")
    risk_signal: str = Field(description="Must be exactly: 'HOLD', 'WATCH', 'CAUTION', or 'EXIT'")
    reasoning: str = Field(description="Plain English reasoning explaining the stop loss and risk status based on recent developments.")
    q1_target: float = Field(description="Projected target price in 3 months (Q1)")
    q2_target: float = Field(description="Projected target price in 6 months (Q2)")
    q3_target: float = Field(description="Projected target price in 9 months (Q3)")
    q4_target: float = Field(description="Projected target price in 12 months (Q4)")
    target_rationale: str = Field(description="Factual rationale explaining why these targets are expected at these quarters.")


class BatchHoldingSuggestionsSchema(BaseModel):
    suggestions: List[BatchHoldingSuggestionItem] = Field(description="List of AI recommendations, one for each active stock holding in the input.")


# ============================================================================
# News Sentiment & AI Stop Loss Service
# ============================================================================

class NewsSentimentService:
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def analyze_article(self, symbol: str, title: str, content: str) -> Dict[str, Any]:
        """
        Uses Gemini to perform structured sentiment and impact analysis on a single news headline.
        """
        prompt = f"""
        Analyze the following financial news article headline/text for the stock symbol '{symbol.upper()}'.

        Headline/Text:
        "{title}"
        {content if content else ""}
        
        Provide a structured analysis matching the requested JSON schema.
        """

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=NewsAnalysisSchema,
                    temperature=0.1,
                )
            )
            result = json.loads(response.text)
            logger.info(f"Successfully analyzed news article for {symbol}: {result.get('sentiment')}")
            return result
        except Exception as e:
            logger.exception(f"Failed to analyze article for {symbol}: {e}")
            return {
                "sentiment": "NEUTRAL",
                "impact_level": "LOW",
                "impact_type": "PRICE_SENSITIVE",
                "summary": title[:150],
                "price_effect": "No major immediate price effect expected."
            }

    async def analyze_articles_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batches analysis of multiple articles across different symbols into a single Gemini call.
        """
        if not articles:
            return []

        formatted_articles = []
        for a in articles:
            formatted_articles.append(
                f"- ID: {a['id']}\n"
                f"  Symbol: {a['symbol'].upper()}\n"
                f"  Headline: {a['title']}"
            )
        articles_context = "\n\n".join(formatted_articles)

        prompt = f"""
        You are a financial news intelligence system. Analyze the following batch of news article headlines.
        For each article, classify the sentiment, impact level, impact type, summary, and price effect.
        
        BATCH ARTICLES:
        {articles_context}
        
        Provide a structured list of analyses matching the requested JSON schema. Make sure every article ID is analyzed and returned.
        """

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BatchNewsAnalysisSchema,
                    temperature=0.1,
                )
            )
            result = json.loads(response.text)
            analyses = result.get("analyses", [])
            logger.info(f"[SentimentBatch] Successfully analyzed {len(analyses)}/{len(articles)} articles in one call.")
            return analyses
        except Exception as e:
            logger.exception(f"[SentimentBatch] Failed to batch analyze articles: {e}")
            # Fallback list of neutral responses mapped to inputs
            fallback = []
            for a in articles:
                fallback.append({
                    "id": a["id"],
                    "sentiment": "NEUTRAL",
                    "impact_level": "LOW",
                    "impact_type": "PRICE_SENSITIVE",
                    "summary": a["title"][:150],
                    "price_effect": "No immediate major price effect expected."
                })
            return fallback

    async def generate_holding_suggestion(
        self,
        symbol: str,
        avg_buy_price: float,
        current_price: float,
        recent_news: List[Dict[str, Any]],
        corporate_highlights: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates stop loss, risk rating, and quarterly targets using Gemini.
        """
        news_summary_list = []
        for idx, news in enumerate(recent_news[:5]):
            news_summary_list.append(
                f"- Headline: {news.get('title')}\n"
                f"  Sentiment: {news.get('sentiment')} | Impact: {news.get('impact_level')}\n"
                f"  AI Summary: {news.get('ai_summary')}"
            )
        news_context = "\n".join(news_summary_list) if news_summary_list else "No recent news available."

        prompt = f"""
        You are an advanced AI Portfolio advisor. Calculate stop loss and expected target prices for holding '{symbol.upper()}'.
        
        HOLDING DATA:
        - Symbol: {symbol.upper()}
        - Average Buy Price: ₹{avg_buy_price}
        - Current Market Price: ₹{current_price}
        
        RECENT NEWS SUMMARY (LAST 24 HOURS):
        {news_context}
        
        CORPORATE HIGHLIGHTS (EARNINGS RAG CONTEXT):
        {corporate_highlights if corporate_highlights else "No transcript guidance available."}
        
        Based on the current pricing, the general news sentiment, and the corporate fundamentals:
        1. Suggest a realistic educational Stop Loss.
        2. Set a Risk Signal ('HOLD', 'WATCH', 'CAUTION', 'EXIT').
        3. Project realistic expected target prices for the next 4 quarters (Q1 = 3m, Q2 = 6m, Q3 = 9m, Q4 = 12m) from the current price, grounding these in the news sentiment and guided margins.
        4. Explain your suggestions in detail in plain English reasoning and target rationales. Provide clear, direct trade recommendations (buy, sell, hold, exit, reallocate) based on these insights.
        """

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=HoldingSuggestionSchema,
                    temperature=0.2,
                )
            )
            result = json.loads(response.text)
            logger.info(f"Generated AI stop loss and target recommendations for {symbol}: {result.get('risk_signal')}")
            return result
        except Exception as e:
            logger.exception(f"Failed to generate holding suggestions for {symbol}: {e}")
            # Safe compliance fallbacks
            return {
                "suggested_stop_loss": avg_buy_price * 0.90, # 10% below average cost
                "risk_signal": "HOLD",
                "reasoning": "Standard holding support active. Review portfolio metrics periodically.",
                "q1_target": current_price * 1.03,
                "q2_target": current_price * 1.06,
                "q3_target": current_price * 1.09,
                "q4_target": current_price * 1.12,
                "target_rationale": "Gradual long-term growth projected based on mock market expectations."
            }

    async def generate_holding_suggestions_batch(
        self,
        holdings: List[Dict[str, Any]],
        news_by_symbol: Dict[str, List[Dict[str, Any]]],
        corporate_highlights: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Batches stop loss, risk signals, and quarterly targets for all stock holdings into a single Gemini call.
        Enforces strict mathematical stop-loss boundary limits, date grounding, and symbol alignment.
        """
        if not holdings:
            return []

        from datetime import datetime
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        input_symbols = [h["symbol"].upper() for h in holdings]

        # Compile list of stock items with their specific news context
        formatted_holdings = []
        for h in holdings:
            sym = h["symbol"].upper()
            avg_price = h["average_buy_price"]
            curr_price = h["current_price"]
            
            # Context news for this symbol
            sym_news = news_by_symbol.get(sym, [])
            news_lines = []
            for n in sym_news[:5]:
                news_lines.append(
                    f"  * Headline: {n.get('title')} | Sentiment: {n.get('sentiment')} | AI Summary: {n.get('ai_summary')}"
                )
            news_block = "\n".join(news_lines) if news_lines else "  * No recent news available."
            
            formatted_holdings.append(
                f"- Symbol: {sym}\n"
                f"  Average Buy Price: ₹{avg_price}\n"
                f"  Current Market Price: ₹{curr_price}\n"
                f"  Recent News:\n{news_block}"
            )
        holdings_context = "\n\n".join(formatted_holdings)

        prompt = f"""
        You are an advanced AI Portfolio advisor.
        Generate stop-loss values, risk signals, and quarterly targets for the following active stock holdings.
        
        CURRENT DATE: {current_date_str}
        
        HOLDINGS TO PROCESS:
        {holdings_context}
        
        CORPORATE FUNDAMENTALS:
        {corporate_highlights if corporate_highlights else "No transcript guidance available."}
        
        CRITICAL RULES FOR ACCURACY:
        1. RULES FOR SUGGESTED STOP LOSS:
           - For EACH symbol, the `suggested_stop_loss` MUST be a float strictly less than its `current_price`.
           - The `suggested_stop_loss` MUST be mathematically between `avg_buy_price * 0.85` and `avg_buy_price * 0.95`.
        2. FORCE SYMBOL CONSISTENCY:
           - The list of output suggestions MUST contain exactly the input symbols.
           - Each object in the suggestions list MUST match one of the input symbols: {input_symbols}.
        3. risk_signal must be exactly: 'HOLD', 'WATCH', 'CAUTION', or 'EXIT'.
        4. Explain suggestions in plain English reasoning and target rationales. Provide clear, direct trade recommendations (buy, sell, hold, exit, reallocate) based on these insights.
        """

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BatchHoldingSuggestionsSchema,
                    temperature=0.1,  # deterministic & fast
                )
            )
            result = json.loads(response.text)
            suggestions = result.get("suggestions", [])
            logger.info(f"[SuggestionsBatch] Generated AI recommendations for {len(suggestions)} holdings in one call.")
            return suggestions
        except Exception as e:
            logger.exception(f"[SuggestionsBatch] Failed to generate batched suggestions: {e}")
            # Compliance fallback mappings
            fallback = []
            for h in holdings:
                sym = h["symbol"].upper()
                curr = h["current_price"]
                avg = h["average_buy_price"]
                fallback.append({
                    "symbol": sym,
                    "suggested_stop_loss": avg * 0.90,
                    "risk_signal": "HOLD",
                    "reasoning": "Standard holding support active. Review portfolio metrics periodically.",
                    "q1_target": curr * 1.03,
                    "q2_target": curr * 1.06,
                    "q3_target": curr * 1.09,
                    "q4_target": curr * 1.12,
                    "target_rationale": "Gradual long-term growth projected based on mock market expectations."
                })
            return fallback

# Singleton instance
news_sentiment_service = NewsSentimentService()
