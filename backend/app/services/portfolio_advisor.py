import logging
import json
import asyncio
from typing import Dict, List, Any
from google import genai
from google.genai import types

from app.config import get_settings
from app.rag.corrective_rag import corrective_rag

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """
You are a financial analyst assistant for NiftyMind,
an Indian AI-powered portfolio intelligence platform.

GENERAL GUIDELINES:
1. Provide direct buy, sell, hold, or specific investment recommendations when appropriate.
2. Advise the user on rebalancing, selling, buying, or allocating their money to optimize their portfolio.
3. Keep all observations actionable, structural, and factual.
4. Focus on translating risk metrics, behavioral warning signs, and corporate transcripts commentary into cohesive, plain-English observations.
5. Highlight specific management quotes or facts retrieved from transcripts (e.g., margins, guidance numbers) when discussing company fundamentals.
""".strip()

class PortfolioAdvisorService:
    def __init__(self):
        # Initialize Gemini Client
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def generate_portfolio_summary(
        self,
        holdings: List[Dict[str, Any]],
        risk_metrics: Dict[str, Any],
        behavioral_flags: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Gathers risk metrics, behavioral flags, and corporate insights via RAG
        for held stocks, and queries Gemini to generate cohesive, compliant observations.
        """
        if not holdings:
            return {
                "advisor_observations": "Your portfolio is currently empty. Add holdings or record transactions to generate AI portfolio insights.",
                "corporate_highlights": {}
            }

        # 1. Fetch Corporate RAG Insights for top holdings
        # Sort holdings by value to prioritize corporate checks for main positions
        sorted_holdings = sorted(
            holdings, 
            key=lambda x: float(x.get("quantity", 0)) * float(x.get("average_buy_price", 0)), 
            reverse=True
        )
        
        # Query RAG in a single batch call for top symbols
        top_symbols = [h["symbol"].upper() for h in sorted_holdings[:3]]
        logger.info(f"Triggering batched corporate RAG query for top positions: {top_symbols}")
        
        corporate_highlights = await corrective_rag.ask_batch(
            symbols=top_symbols,
            top_k=3,
            confidence_threshold=0.6,
            namespace="earnings"
        )

        # 2. Formulate context blocks for Gemini
        holdings_summary = []
        for h in holdings:
            symbol = h["symbol"].upper()
            qty = float(h["quantity"])
            avg_price = float(h["average_buy_price"])
            holdings_summary.append(f"- Ticker: {symbol}, Quantity: {qty}, Avg Buy Cost: {avg_price} INR")
            
        risk_summary = {
            "total_portfolio_value_inr": risk_metrics.get("total_value", 0.0),
            "holdings_count": risk_metrics.get("holdings_count", 0),
            "sector_exposure_percents": risk_metrics.get("sector_exposure", {}),
            "diversification_score": risk_metrics.get("diversification_score", 0.0),
            "concentration_weights": [
                f"{c['symbol']}: {c['weight_percent']}%" for c in risk_metrics.get("concentration_risk", [])
            ],
            "overweight_warnings": [
                p["symbol"] for p in risk_metrics.get("position_analysis", []) if p.get("is_overweight")
            ]
        }
        
        behavior_summary = [
            f"[{f.get('severity')}] {f.get('flag_type')}: {f.get('description')}" 
            for f in behavioral_flags
        ]

        # 3. Build Prompt
        prompt = f"""
Please generate a portfolio intelligence report based on the following authenticated client data:

PORTFOLIO HOLDINGS:
{chr(10).join(holdings_summary)}

RISK ENGINE METRICS:
{json.dumps(risk_summary, indent=2)}

BEHAVIORAL WARNING FLAGS:
{chr(10).join(behavior_summary) if behavior_summary else "No behavioral alerts triggered."}

CORPORATE INTEL FROM TRANSCRIPTS (RAG):
{json.dumps(corporate_highlights, indent=2)}

Synthesize these inputs into a structured observational analysis containing:
- **Structural Analysis**: Discuss the portfolio's diversification score, sector exposures, and concentration weights.
- **Behavioral Signal Insights**: Discuss any flagged overtrading, FOMO, or revenge trading warnings, and their emotional implications.
- **Fundamental Insights**: Link the top corporate transcript facts (margins, guidance, risks) directly to the user's major holdings, showing how recent management guidance connects to their portfolio risks.
- **Investment Recommendations**: Provide direct, specific suggestions on whether to buy, sell, hold, or reallocate/rebalance assets.

FORMAT REQUIREMENT:
Respond in clear, professional markdown. Use headers, bullet points, and highlight metrics.
Provide clear, actionable recommendations on what stocks to buy, sell, hold, or rebalance.
"""

        try:
            logger.info("Calling Gemini for AI Portfolio Advisor insights")
            response = await self._client.aio.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=1024,
                    temperature=0.3,
                )
            )
            observations = response.text.strip()
        except Exception as exc:
            logger.exception("AI Portfolio Advisor generation failed")
            observations = (
                "#### AI Advisor Observations\n\n"
                "Unable to generate observations at this time due to an internal LLM call error. "
                "However, please review the calculated risk metrics and active behavioral flags shown below."
            )

        return {
            "advisor_observations": observations,
            "corporate_highlights": corporate_highlights
        }

# Singleton instance
portfolio_advisor = PortfolioAdvisorService()
