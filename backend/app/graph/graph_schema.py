import logging
from typing import Dict, List

from app.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


# Static knowledge graph data
COMPANIES = [
    {"ticker": "INFY", "name": "Infosys Limited", "sector": "Information Technology", "exchange": "NSE", "index": "NIFTY"},
    {"ticker": "TCS", "name": "Tata Consultancy Services Limited", "sector": "Information Technology", "exchange": "NSE", "index": "NIFTY"},
    {"ticker": "HDFCBANK", "name": "HDFC Bank Limited", "sector": "Banking", "exchange": "NSE", "index": "NIFTY"},
]

EARNINGS_EVENTS = [
    {"id": "INFY_Q3_FY2025", "company_ticker": "INFY", "quarter": "Q3 FY2025", "date": "2025-01-25", "transcript_id": "transcript_infy_q3_2025"},
    {"id": "TCS_Q3_FY2025", "company_ticker": "TCS", "quarter": "Q3 FY2025", "date": "2025-01-24", "transcript_id": "transcript_tcs_q3_2025"},
    {"id": "HDFCBANK_Q3_FY2025", "company_ticker": "HDFCBANK", "quarter": "Q3 FY2025", "date": "2025-01-26", "transcript_id": "transcript_hdfcbank_q3_2025"},
]

FINANCIAL_METRICS = [
    {"event_id": "INFY_Q3_FY2025", "type": "operating_margin", "value": 21.3, "unit": "%", "direction": "stable"},
    {"event_id": "TCS_Q3_FY2025", "type": "ebit_margin", "value": 24.5, "unit": "%", "direction": "improving"},
    {"event_id": "INFY_Q3_FY2025", "type": "revenue_usd", "value": 4.7, "unit": "B", "direction": "up"},
    {"event_id": "TCS_Q3_FY2025", "type": "revenue_usd", "value": 7.5, "unit": "B", "direction": "up"},
    {"event_id": "HDFCBANK_Q3_FY2025", "type": "net_interest_margin", "value": 3.4, "unit": "%", "direction": "stable"},
    {"event_id": "HDFCBANK_Q3_FY2025", "type": "gross_npa", "value": 1.26, "unit": "%", "direction": "improving"},
    {"event_id": "HDFCBANK_Q3_FY2025", "type": "return_on_equity", "value": 15.8, "unit": "%", "direction": "stable"},
    # additional sample metrics to reach 12 entries
    {"event_id": "INFY_Q3_FY2025", "type": "ebit_margin", "value": 20.0, "unit": "%", "direction": "stable"},
    {"event_id": "TCS_Q3_FY2025", "type": "operating_margin", "value": 22.0, "unit": "%", "direction": "stable"},
    {"event_id": "INFY_Q3_FY2025", "type": "net_profit", "value": 1.05, "unit": "B", "direction": "up"},
    {"event_id": "TCS_Q3_FY2025", "type": "net_profit", "value": 1.8, "unit": "B", "direction": "up"},
    {"event_id": "HDFCBANK_Q3_FY2025", "type": "operating_margin", "value": 18.2, "unit": "%", "direction": "stable"},
]

CORPORATE_ACTIONS = [
    {"company_ticker": "INFY", "type": "dividend", "amount": 21, "unit": "INR", "subtype": "regular", "quarter": "Q3 FY2025"},
    {"company_ticker": "INFY", "type": "buyback", "amount": 9200, "unit": "CR", "subtype": "share_buyback", "quarter": "Q3 FY2025"},
    {"company_ticker": "TCS", "type": "dividend", "amount": 76, "unit": "INR", "subtype": "regular", "quarter": "Q3 FY2025"},
    {"company_ticker": "TCS", "type": "special_dividend", "amount": 400, "unit": "INR", "subtype": "special", "quarter": "Q3 FY2025"},
    {"company_ticker": "TCS", "type": "buyback", "amount": 17000, "unit": "CR", "subtype": "share_buyback", "quarter": "Q3 FY2025"},
    {"company_ticker": "HDFCBANK", "type": "dividend", "amount": 19.5, "unit": "INR", "subtype": "regular", "quarter": "Q3 FY2025"},
]

COMPETITOR_RELATIONSHIPS = [
    {"ticker_a": "INFY", "ticker_b": "TCS"},
]


def setup_constraints() -> None:
    """Create uniqueness constraints if they do not exist."""
    statements = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (e:EarningsEvent) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE",
    ]
    for s in statements:
        neo4j_client.run_query(s)
    logger.info("Graph constraints ensured")


def ingest_knowledge_graph() -> Dict[str, int]:
    """Ingest the static schema into the Neo4j database and return counts."""
    # 1. Sectors
    sectors = {c["sector"] for c in COMPANIES}
    for sector in sectors:
        cypher = "MERGE (s:Sector {name: $name})"
        neo4j_client.run_query(cypher, {"name": sector})

    # 2. Companies and BELONGS_TO
    for comp in COMPANIES:
        cypher = (
            "MERGE (c:Company {ticker: $ticker}) "
            "SET c.name = $name, c.exchange = $exchange, c.index = $index "
            "WITH c "
            "MATCH (s:Sector {name: $sector}) "
            "MERGE (c)-[:BELONGS_TO]->(s)"
        )
        neo4j_client.run_query(cypher, {"ticker": comp["ticker"], "name": comp["name"], "exchange": comp["exchange"], "index": comp["index"], "sector": comp["sector"]})

    # 3. Earnings events
    for ev in EARNINGS_EVENTS:
        cypher = (
            "MERGE (e:EarningsEvent {id: $id}) "
            "SET e.quarter = $quarter, e.date = $date, e.transcript_id = $transcript_id "
            "WITH e "
            "MATCH (c:Company {ticker: $ticker}) "
            "MERGE (c)-[:REPORTED]->(e)"
        )
        neo4j_client.run_query(cypher, {"id": ev["id"], "quarter": ev["quarter"], "date": ev["date"], "transcript_id": ev["transcript_id"], "ticker": ev["company_ticker"]})

    # 4. Financial metrics
    for m in FINANCIAL_METRICS:
        metric_id = f"{m['event_id']}_{m['type']}"
        cypher = (
            "MERGE (mm:FinancialMetric {id: $id}) "
            "SET mm.type = $type, mm.value = $value, mm.unit = $unit, mm.direction = $direction "
            "WITH mm "
            "MATCH (e:EarningsEvent {id: $event_id}) "
            "MERGE (e)-[:HAS_METRIC]->(mm)"
        )
        neo4j_client.run_query(cypher, {"id": metric_id, "type": m["type"], "value": m["value"], "unit": m["unit"], "direction": m["direction"], "event_id": m["event_id"]})

    # 5. Corporate actions
    for a in CORPORATE_ACTIONS:
        action_id = f"{a['company_ticker']}_{a['type']}_{a['quarter']}"
        cypher = (
            "MERGE (ca:CorporateAction {id: $id}) "
            "SET ca.type = $type, ca.amount = $amount, ca.unit = $unit, ca.subtype = $subtype, ca.quarter = $quarter "
            "WITH ca "
            "MATCH (c:Company {ticker: $ticker}) "
            "MERGE (c)-[:DECLARED]->(ca)"
        )
        neo4j_client.run_query(cypher, {"id": action_id, "type": a["type"], "amount": a["amount"], "unit": a["unit"], "subtype": a.get("subtype",""), "quarter": a["quarter"], "ticker": a["company_ticker"]})

    # 6. Competitor relationships
    for rel in COMPETITOR_RELATIONSHIPS:
        cypher = (
            "MATCH (a:Company {ticker: $a}), (b:Company {ticker: $b}) "
            "MERGE (a)-[:COMPETES_WITH]->(b) "
            "MERGE (b)-[:COMPETES_WITH]->(a)"
        )
        neo4j_client.run_query(cypher, {"a": rel["ticker_a"], "b": rel["ticker_b"]})

    # Return counts
    stats = {}
    for label in ["Company", "Sector", "EarningsEvent", "FinancialMetric", "CorporateAction"]:
        res = neo4j_client.run_query(f"MATCH (n:{label}) RETURN count(n) as count")
        stats[label] = res[0]["count"] if res else 0

    logger.info("Knowledge graph ingested", extra={"stats": stats})
    return stats
