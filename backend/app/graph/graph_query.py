import logging
from typing import Any, Dict, List, Optional

from app.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class GraphQueryService:
    def get_company_overview(self, ticker: str) -> Dict[str, Any]:
        cypher = (
            "MATCH (c:Company {ticker: $ticker}) "
            "OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Sector) "
            "OPTIONAL MATCH (c)-[:REPORTED]->(e:EarningsEvent) "
            "OPTIONAL MATCH (c)-[:DECLARED]->(a:CorporateAction) "
            "RETURN c.name AS name, c.ticker AS ticker, s.name AS sector, collect(DISTINCT e.quarter) AS quarters, collect(DISTINCT {type: a.type, amount: a.amount, unit: a.unit, subtype: a.subtype, quarter: a.quarter}) AS actions"
        )
        res = neo4j_client.run_query(cypher, {"ticker": ticker})
        return res[0] if res else {}

    def get_sector_companies(self, sector: str) -> List[Dict[str, Any]]:
        cypher = (
            "MATCH (c:Company)-[:BELONGS_TO]->(s:Sector) "
            "WHERE toLower(s.name) CONTAINS toLower($sector) "
            "RETURN c.ticker AS ticker, c.name AS name, s.name AS sector"
        )
        return neo4j_client.run_query(cypher, {"sector": sector})

    def get_companies_by_metric(self, metric_type: str, min_value: Optional[float] = None, quarter: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"metric_type": metric_type}
        filters = ["m.type = $metric_type"]
        if min_value is not None:
            filters.append("m.value >= $min_value")
            params["min_value"] = min_value
        if quarter:
            filters.append("e.quarter = $quarter")
            params["quarter"] = quarter

        where_clause = " AND ".join(filters)
        cypher = (
            "MATCH (c:Company)-[:REPORTED]->(e:EarningsEvent)-[:HAS_METRIC]->(m:FinancialMetric) "
            f"WHERE {where_clause} "
            "RETURN c.ticker AS ticker, c.name AS name, e.quarter AS quarter, m.value AS value, m.unit AS unit, m.direction AS direction ORDER BY m.value DESC"
        )
        return neo4j_client.run_query(cypher, params)

    def get_corporate_actions(self, ticker: Optional[str] = None, action_type: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        clauses = ["(c:Company)-[:DECLARED]->(a:CorporateAction)"]
        if ticker:
            clauses.append("c.ticker = $ticker")
            params["ticker"] = ticker
        if action_type:
            clauses.append("a.type = $action_type")
            params["action_type"] = action_type

        where = " AND ".join(clauses[1:]) if len(clauses) > 1 else ""
        cypher = (
            "MATCH (c:Company)-[:DECLARED]->(a:CorporateAction) "
            + (f"WHERE {where} " if where else "")
            + "RETURN c.ticker AS ticker, c.name AS company, a.type AS action_type, a.amount AS amount, a.unit AS unit, a.subtype AS subtype, a.quarter AS quarter"
        )
        return neo4j_client.run_query(cypher, params)

    def get_competitors(self, ticker: str) -> List[Dict[str, Any]]:
        cypher = (
            "MATCH (c:Company {ticker: $ticker})-[:COMPETES_WITH]->(o:Company) "
            "RETURN o.ticker AS ticker, o.name AS name"
        )
        return neo4j_client.run_query(cypher, {"ticker": ticker})

    def get_graph_stats(self) -> Dict[str, int]:
        cypher = (
            "RETURN size((:Company)) AS companies, size((:Sector)) AS sectors, size((:EarningsEvent)) AS events, size((:FinancialMetric)) AS metrics, size((:CorporateAction)) AS actions"
        )
        res = neo4j_client.run_query(cypher)
        return res[0] if res else {}

    def natural_language_to_graph(self, question: str) -> List[Dict[str, Any]]:
        q = question.lower()
        if "dividend" in q:
            return self.get_corporate_actions(action_type="dividend")
        if "buyback" in q:
            return self.get_corporate_actions(action_type="buyback")
        if "margin" in q or "profit" in q:
            return self.get_companies_by_metric("operating_margin")
        if "bank" in q or "npa" in q:
            return self.get_sector_companies("Banking")
        if "it" in q or "technology" in q:
            return self.get_sector_companies("Information Technology")
        # default
        return self.get_corporate_actions()

    def get_portfolio_dependencies(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves all graph connections (Sectors, Competitors, Clients, Vendors)
        for a list of portfolio company tickers. Returns a unified edge list.
        """
        if not symbols:
            return []
        
        symbols_upper = [s.strip().upper() for s in symbols if s]
        
        cypher = """
        // 1. Sector connections
        MATCH (c:Company)-[r:BELONGS_TO]->(s:Sector)
        WHERE c.ticker IN $symbols
        RETURN c.ticker as source, s.name as target, "BELONGS_TO" as type, {} as properties
        
        UNION
        
        // 2. Competitor connections
        MATCH (c:Company)-[r:COMPETES_WITH]->(other:Company)
        WHERE c.ticker IN $symbols
        RETURN c.ticker as source, other.ticker as target, "COMPETES_WITH" as type, {} as properties
        
        UNION
        
        // 3. Client connections (Company is the vendor)
        MATCH (c:Company)-[r:VENDOR_OF]->(other:Company)
        WHERE c.ticker IN $symbols
        RETURN c.ticker as source, other.ticker as target, "VENDOR_OF" as type, 
               {category: coalesce(r.category, 'General Services'), reliance: coalesce(r.reliance, 'MEDIUM')} as properties
               
        UNION
        
        // 4. Vendor connections (Company is the client)
        MATCH (other:Company)-[r:VENDOR_OF]->(c:Company)
        WHERE c.ticker IN $symbols
        RETURN other.ticker as source, c.ticker as target, "VENDOR_OF" as type, 
               {category: coalesce(r.category, 'General Services'), reliance: coalesce(r.reliance, 'MEDIUM')} as properties
        """
        return neo4j_client.run_query(cypher, {"symbols": symbols_upper})


# module-level singleton
graph_query = GraphQueryService()

