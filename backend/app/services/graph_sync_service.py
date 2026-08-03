import logging
import json
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from app.config import get_settings
from app.graph.neo4j_client import neo4j_client
from app.db.session import pg_pool, init_pg_pool

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================================
# Pydantic Schemas for Structured Output
# ============================================================================

class RelationshipItem(BaseModel):
    name_or_ticker: str = Field(description="The standard stock ticker (e.g. 'HDFCBANK', 'TCS') if listed on NSE/BSE, or the full company name if unlisted.")
    category: str = Field(description="The business category, e.g. 'Core Banking', 'Cloud Infrastructure', 'Audit Services', 'Supply of steel'.")
    reliance: str = Field(description="Must be exactly: 'HIGH', 'MEDIUM', or 'LOW'")

class CompanyDetailsSchema(BaseModel):
    name: str = Field(description="Full official company name (e.g. Tata Consultancy Services Limited)")
    sector: str = Field(description="Must be exactly: 'Information Technology', 'Banking', 'Auto', 'Finance', 'Energy', 'Consumer Goods', 'Real Estate', 'Healthcare', 'Materials', or 'Utilities'")
    competitors: List[str] = Field(description="List of standard stock tickers for up to 3 major listed competitors in India (e.g. ['INFY', 'WIPRO', 'LTIM'])")
    clients: List[RelationshipItem] = Field(description="List of up to 3 major customer/client companies.")
    vendors: List[RelationshipItem] = Field(description="List of up to 3 major supplier/vendor companies.")

# ============================================================================
# Graph Sync Service
# ============================================================================

class GraphSyncService:
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def ensure_company_mapped(self, symbol: str) -> None:
        """
        Dynamically verifies if a company is mapped in Neo4j.
        If missing, uses Gemini to extract its metadata and connections, then ingests them.
        """
        symbol_upper = symbol.strip().upper()
        if not symbol_upper:
            return

        # 1. Check if already exists in Neo4j
        check_query = "MATCH (c:Company {ticker: $ticker}) RETURN c.ticker AS ticker"
        res = neo4j_client.run_query(check_query, {"ticker": symbol_upper})
        if res:
            logger.info(f"[GraphSync] Company '{symbol_upper}' is already mapped. Skipping.")
            return

        logger.info(f"[GraphSync] Company '{symbol_upper}' is missing from Neo4j. Triggering dynamic extraction...")

        # 2. Call Gemini with Structured Outputs to extract company details and relations
        prompt = f"""
        You are an expert financial systems data engineer.
        Analyze the Indian listed stock symbol '{symbol_upper}'.
        
        Retrieve or deduce:
        1. Its full official corporate name (e.g., 'TCS' -> 'Tata Consultancy Services Limited').
        2. Its primary GICS industry sector (Information Technology, Banking, Auto, Finance, Energy, Consumer Goods, Real Estate, Healthcare, Materials, Utilities).
        3. Up to 3 major competitor tickers listed in India.
        4. Up to 3 key client/customer companies. Return their NSE tickers if they are listed public companies in India, or full names if private/unlisted.
        5. Up to 3 key vendor/supplier companies. Return their NSE tickers if listed, or full names if private/unlisted.
        
        Provide your analysis in the requested JSON structure.
        """

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CompanyDetailsSchema,
                    temperature=0.1,
                )
            )
            data = json.loads(response.text)
            logger.info(f"[GraphSync] Extracted metadata for {symbol_upper}: Name={data.get('name')}, Sector={data.get('sector')}")
        except Exception as e:
            logger.error(f"[GraphSync] Gemini extraction failed for {symbol_upper}: {e}", exc_info=True)
            return

        # 3. Clean and resolve tickers (Fuzzy Entity Resolution)
        resolved_competitors = [c.strip().upper() for c in data.get("competitors", [])]
        
        # Resolve clients and vendors text names to tickers using DB check if needed
        resolved_clients = await self._resolve_relationships(data.get("clients", []))
        resolved_vendors = await self._resolve_relationships(data.get("vendors", []))

        # 4. Ingest into Neo4j
        try:
            # Create Company and Sector
            neo4j_client.run_query(
                "MERGE (s:Sector {name: $sector})",
                {"sector": data["sector"]}
            )
            neo4j_client.run_query(
                "MERGE (c:Company {ticker: $ticker}) SET c.name = $name",
                {"ticker": symbol_upper, "name": data["name"]}
            )
            neo4j_client.run_query(
                "MATCH (c:Company {ticker: $ticker}), (s:Sector {name: $sector}) MERGE (c)-[:BELONGS_TO]->(s)",
                {"ticker": symbol_upper, "sector": data["sector"]}
            )

            # Ingest Competitors
            for comp in resolved_competitors:
                neo4j_client.run_query(
                    "MERGE (comp:Company {ticker: $comp_ticker}) WITH comp "
                    "MATCH (c:Company {ticker: $ticker}) "
                    "MERGE (c)-[:COMPETES_WITH]->(comp) "
                    "MERGE (comp)-[:COMPETES_WITH]->(c)",
                    {"ticker": symbol_upper, "comp_ticker": comp}
                )

            # Ingest Clients (Vendor -> Client relationship)
            for cl in resolved_clients:
                neo4j_client.run_query(
                    "MERGE (client:Company {ticker: $client_ticker}) WITH client "
                    "MATCH (c:Company {ticker: $ticker}) "
                    "MERGE (c)-[:VENDOR_OF {category: $category, reliance: $reliance}]->(client)",
                    {
                        "ticker": symbol_upper, 
                        "client_ticker": cl["resolved_ticker"],
                        "category": cl["category"],
                        "reliance": cl["reliance"]
                    }
                )

            # Ingest Vendors (Vendor -> Company relationship)
            for v in resolved_vendors:
                neo4j_client.run_query(
                    "MERGE (vendor:Company {ticker: $vendor_ticker}) WITH vendor "
                    "MATCH (c:Company {ticker: $ticker}) "
                    "MERGE (vendor)-[:VENDOR_OF {category: $category, reliance: $reliance}]->(c)",
                    {
                        "ticker": symbol_upper, 
                        "vendor_ticker": v["resolved_ticker"],
                        "category": v["category"],
                        "reliance": v["reliance"]
                    }
                )

            logger.info(f"[GraphSync] Successfully completed Neo4j mapping for '{symbol_upper}'")
        except Exception as ex:
            logger.error(f"[GraphSync] Neo4j writes failed for {symbol_upper}: {ex}", exc_info=True)

    async def _resolve_relationships(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolves raw client/vendor names or tickers to standard stock tickers using DB constraints."""
        resolved = []
        
        # Initialize pg pool if not done
        global pg_pool
        if pg_pool is None:
            await init_pg_pool()

        for item in relations:
            name_raw = item.get("name_or_ticker", "").strip().upper()
            if not name_raw:
                continue

            category = item.get("category", "General business")
            reliance = item.get("reliance", "MEDIUM").upper()
            if reliance not in ("HIGH", "MEDIUM", "LOW"):
                reliance = "MEDIUM"

            # Check if it looks like a ticker (short, single-word)
            if len(name_raw) <= 10 and " " not in name_raw:
                resolved.append({
                    "resolved_ticker": name_raw,
                    "category": category,
                    "reliance": reliance
                })
                continue

            # Otherwise, fuzzy-match using our SQL database `stock_prices` or standard mapping
            if pg_pool:
                try:
                    async with pg_pool.acquire() as conn:
                        row = await conn.fetchrow(
                            "SELECT symbol FROM stock_prices WHERE symbol = $1 OR symbol ILIKE $2 LIMIT 1",
                            name_raw, f"%{name_raw}%"
                        )
                        if row:
                            ticker = row["symbol"].upper()
                            resolved.append({
                                "resolved_ticker": ticker,
                                "category": category,
                                "reliance": reliance
                            })
                            continue
                except Exception as e:
                    logger.debug(f"[GraphSync] Fuzzy SQL resolution failed for '{name_raw}': {e}")

            # Fallback: Clean the name to create a safe uppercase unlisted ticker (alphanumeric only)
            sanitized = "".join(ch for ch in name_raw if ch.isalnum())[:12]
            resolved.append({
                "resolved_ticker": sanitized,
                "category": category,
                "reliance": reliance
            })

        return resolved

# Singleton instance
graph_sync_service = GraphSyncService()
