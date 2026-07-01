import logging
import json
import asyncio
from typing import Optional

from google import genai
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded

from app.config import get_settings
from app.analytics.fno.models.option_chain import OptionChainMetrics
from app.analytics.fno.models.oi_delta import OIDeltaReport, SpikeSeverity
from app.analytics.fno.models.analysis import MarketNarrative

logger = logging.getLogger(__name__)
settings = get_settings()

# Create Gemini client once at module load
client = genai.Client(
    api_key=settings.gemini_api_key
)

SYSTEM_PROMPT = """
You are a SEBI-registered market analyst assistant for NiftyMind,
an Indian F&O analytics platform.

STRICT COMPLIANCE RULES — never violate these:
1. NEVER give buy, sell, or hold recommendations.
2. NEVER predict future price direction with certainty.
3. NEVER use phrases like "will go up", "guaranteed", "sure shot".
4. ALWAYS use educational, observational language:
   — "OI data suggests...", "traders appear to be...", "historically..."
5. Keep responses factual, data-driven, and neutral.
6. Responses must be concise — no padding, no repetition.

Your role is to translate raw F&O metrics into plain English
observations that help traders understand market structure —
not to advise them on what to do.
""".strip()


class NLPTranslatorService:
    """
    Translates raw OI metrics and delta reports into SEBI-compliant
    natural language market narratives using Google Gemini.
    Falls back to rule-based summary on any API failure.
    """

    def __init__(self):
        self._client = client

    async def translate(
        self,
        metrics: OptionChainMetrics,
        delta: Optional[OIDeltaReport] = None,
    ) -> MarketNarrative:
        """
        Main entry point. Always returns a MarketNarrative — never raises.
        Falls back to rule-based text if Gemini API fails.
        """
        try:
            return await self._call_gemini(metrics, delta)

        except ResourceExhausted:
            logger.warning(
                "Gemini rate limit hit — using rule-based fallback",
                extra={"underlying": metrics.underlying},
            )
            return self._rule_based_fallback(metrics, delta)

        except DeadlineExceeded:
            logger.warning(
                "Gemini timeout — using rule-based fallback",
                extra={"underlying": metrics.underlying},
            )
            return self._rule_based_fallback(metrics, delta)

        except Exception as exc:
            logger.error(
                "Unexpected error in Gemini translation — using fallback",
                extra={
                    "underlying": metrics.underlying,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return self._rule_based_fallback(metrics, delta)

    async def _call_gemini(
        self,
        metrics: OptionChainMetrics,
        delta: Optional[OIDeltaReport],
    ) -> MarketNarrative:
        """
        Constructs prompt, calls Gemini, parses response.
        """

        user_prompt = self._build_prompt(metrics, delta)

        logger.info(
            "Calling Gemini for NLP translation",
            extra={
                "underlying": metrics.underlying,
                "model": settings.model_name,
                "has_delta": delta is not None,
            },
        )

        # Run blocking SDK call in thread for async compatibility
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=settings.model_name,
            contents=f"{SYSTEM_PROMPT}\n\n{user_prompt}",
        )

        raw_text = response.text.strip()

        logger.info(
            "Gemini response received",
            extra={
                "underlying": metrics.underlying,
            },
        )

        return self._parse_response(raw_text, metrics, delta)

    def _build_prompt(
        self,
        metrics: OptionChainMetrics,
        delta: Optional[OIDeltaReport],
    ) -> str:
        """
        Builds a structured JSON prompt for consistent LLM output.
        """

        metrics_block = {
            "underlying": metrics.underlying,
            "spot_price": metrics.spot_price,
            "expiry_date": metrics.expiry_date,
            "pcr": metrics.pcr,
            "pcr_signal": metrics.pcr_signal,
            "total_call_oi": metrics.total_call_oi,
            "total_put_oi": metrics.total_put_oi,
            "max_pain_strike": metrics.max_pain_strike,
            "max_pain_distance_percent": metrics.max_pain_distance_percent,
            "top_call_oi_strikes": [
                {
                    "strike": s.strike_price,
                    "oi": s.open_interest,
                    "oi_change_pct": s.oi_change_percent,
                }
                for s in metrics.top_call_oi_strikes
            ],
            "top_put_oi_strikes": [
                {
                    "strike": s.strike_price,
                    "oi": s.open_interest,
                    "oi_change_pct": s.oi_change_percent,
                }
                for s in metrics.top_put_oi_strikes
            ],
        }

        prompt = f"""
Analyze this F&O option chain data for {metrics.underlying}.

CURRENT SNAPSHOT METRICS:
{json.dumps(metrics_block, indent=2)}
"""

        if delta:
            critical_spikes = [
                {
                    "strike": s.strike_price,
                    "side": s.side,
                    "oi_change_pct": s.oi_change_percent,
                    "type": s.spike_type,
                    "severity": s.severity,
                }
                for s in delta.spike_alerts
                if s.severity == SpikeSeverity.HIGH
            ]

            delta_block = {
                "pcr_previous": delta.pcr_previous,
                "pcr_current": delta.pcr_current,
                "pcr_delta": delta.pcr_delta,
                "pcr_sentiment": delta.pcr_sentiment,
                "time_delta_seconds": delta.time_delta_seconds,
                "total_spike_count": delta.spike_count,
                "critical_spikes": critical_spikes,
            }

            prompt += f"""
CHANGES FROM PREVIOUS SNAPSHOT ({delta.time_delta_seconds:.0f}s ago):
{json.dumps(delta_block, indent=2)}
"""

        prompt += """
Respond in this EXACT format — no preamble, no extra text:

SNAPSHOT_SUMMARY: [2-3 sentences on current market structure and institutional positioning based on OI data]

DELTA_INSIGHT: [2-3 sentences on what changed and what it implies. Write "N/A" if no delta data provided.]

KEY_LEVELS: [1-2 sentences identifying strongest support and resistance strikes based on OI concentration]

SENTIMENT_SUMMARY: [One sentence — overall market mood based on PCR and OI]

Remember: No buy/sell advice. Educational, observational language only.
"""

        return prompt.strip()

    def _parse_response(
        self,
        raw_text: str,
        metrics: OptionChainMetrics,
        delta: Optional[OIDeltaReport],
    ) -> MarketNarrative:
        """
        Parses Gemini's structured response into a MarketNarrative.
        """

        sections: dict[str, str] = {
            "SNAPSHOT_SUMMARY": "",
            "DELTA_INSIGHT": "",
            "KEY_LEVELS": "",
            "SENTIMENT_SUMMARY": "",
        }

        current_key = None

        for line in raw_text.split("\n"):
            line = line.strip()

            matched = False

            for key in sections:
                if line.startswith(f"{key}:"):
                    current_key = key
                    sections[key] = line[len(key) + 1:].strip()
                    matched = True
                    break

            if not matched and current_key and line:
                sections[current_key] += " " + line

        return MarketNarrative(
            snapshot_summary=(
                sections["SNAPSHOT_SUMMARY"]
                or metrics.market_sentiment
            ),
            delta_insight=(
                sections["DELTA_INSIGHT"]
                if delta and sections["DELTA_INSIGHT"] not in ("", "N/A")
                else None
            ),
            key_levels=sections["KEY_LEVELS"] or None,
            sentiment_summary=(
                sections["SENTIMENT_SUMMARY"]
                or metrics.pcr_signal
            ),
            generated_by=settings.model_name,
            is_fallback=False,
        )

    def _rule_based_fallback(
        self,
        metrics: OptionChainMetrics,
        delta: Optional[OIDeltaReport],
    ) -> MarketNarrative:
        """
        Returns rule-based narrative when Gemini is unavailable.
        """

        snapshot_summary = (
            f"{metrics.underlying} trading at {metrics.spot_price}. "
            f"PCR at {metrics.pcr:.2f} signals "
            f"{metrics.pcr_signal} sentiment. "
            f"Max pain at {metrics.max_pain_strike}, "
            f"{metrics.max_pain_distance_percent:.1f}% from spot."
        )

        delta_insight = None

        if delta:
            delta_insight = (
                f"PCR shifted {delta.pcr_delta:+.4f} over "
                f"{delta.time_delta_seconds:.0f}s "
                f"({delta.pcr_sentiment.value}). "
                f"{delta.spike_count} OI spike(s) detected."
            )

        key_levels = None

        if (
            metrics.top_call_oi_strikes
            and metrics.top_put_oi_strikes
        ):
            key_levels = (
                f"Resistance at "
                f"{metrics.top_call_oi_strikes[0].strike_price} CE. "
                f"Support at "
                f"{metrics.top_put_oi_strikes[0].strike_price} PE."
            )

        return MarketNarrative(
            snapshot_summary=snapshot_summary,
            delta_insight=delta_insight,
            key_levels=key_levels,
            sentiment_summary=(
                f"Overall sentiment: {metrics.pcr_signal}."
            ),
            generated_by=settings.model_name,
            is_fallback=True,
        )


# Module-level singleton
nlp_translator = NLPTranslatorService()