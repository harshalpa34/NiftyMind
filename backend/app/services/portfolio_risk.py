import logging
from typing import Dict, List, Any
from app.graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)

# Static fallback sector mapping for NSE stock symbols
FALLBACK_SECTORS = {
    "INFY": "Information Technology",
    "TCS": "Information Technology",
    "HDFCBANK": "Banking",
    "RELIANCE": "Energy",
    "ITC": "Consumer Goods",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "BHARTIARTL": "Telecom",
    "TATASTEEL": "Metals",
    "LTIM": "Information Technology",
    "WIPRO": "Information Technology",
    "HCLTECH": "Information Technology",
}

# Mock market prices for known NSE stocks
MOCK_MARKET_PRICES = {
    "INFY": 1850.0,
    "TCS": 3900.0,
    "HDFCBANK": 1600.0,
    "RELIANCE": 2450.0,
    "ITC": 420.0,
    "ICICIBANK": 1150.0,
    "SBIN": 830.0,
    "BHARTIARTL": 1400.0,
    "TATASTEEL": 180.0,
    "LTIM": 4800.0,
    "WIPRO": 470.0,
    "HCLTECH": 1320.0,
}

class PortfolioRiskService:
    """Service for calculating portfolio risk, sector exposure, and concentration metrics."""

    def get_symbol_sector(self, symbol: str) -> str:
        """Resolve stock sector using Neo4j lookup with a local dictionary fallback."""
        symbol_upper = symbol.strip().upper()
        
        # 1. Try Neo4j lookup
        try:
            if neo4j_client.is_connected():
                cypher = """
                    MATCH (c:Company {ticker: $symbol})-[:BELONGS_TO]->(s:Sector)
                    RETURN s.name AS sector
                """
                results = neo4j_client.run_query(cypher, {"symbol": symbol_upper})
                if results and results[0].get("sector"):
                    return results[0]["sector"]
        except Exception as e:
            logger.warning(f"Neo4j sector lookup failed for '{symbol_upper}': {e}")
            
        # 2. Fall back to local dictionary
        return FALLBACK_SECTORS.get(symbol_upper, "Other / Unclassified")

    def get_current_price(self, symbol: str, avg_buy_price: float, price_map: Dict[str, float] = None) -> float:
        """Resolve current spot price using DB prices, mock data, or falling back to avg buy price."""
        symbol_upper = symbol.strip().upper()
        if price_map and symbol_upper in price_map:
            return price_map[symbol_upper]
        return MOCK_MARKET_PRICES.get(symbol_upper, avg_buy_price)

    def calculate_risk_metrics(
        self, 
        holdings: List[Dict[str, Any]], 
        price_map: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Calculate exposure, concentration, and diversification metrics.
        """
        if not holdings:
            return {
                "total_value": 0.0,
                "holdings_count": 0,
                "sector_exposure": {},
                "concentration_risk": [],
                "diversification_score": 100.0,
                "position_analysis": []
            }

        total_value = 0.0
        calculated_positions = []
        
        # 1. Compute values for each holding
        for h in holdings:
            symbol = h["symbol"].upper()
            qty = float(h["quantity"])
            avg_price = float(h["average_buy_price"])
            
            curr_price = self.get_current_price(symbol, avg_price, price_map)
            pos_value = qty * curr_price
            total_value += pos_value
            
            sector = self.get_symbol_sector(symbol)
            calculated_positions.append({
                "symbol": symbol,
                "quantity": qty,
                "average_buy_price": avg_price,
                "current_price": curr_price,
                "value": pos_value,
                "sector": sector
            })
            
        if total_value == 0:
            return {
                "total_value": 0.0,
                "holdings_count": len(holdings),
                "sector_exposure": {},
                "concentration_risk": [],
                "diversification_score": 0.0,
                "position_analysis": []
            }

        # 2. Group by sector & calculate weights
        sector_totals: Dict[str, float] = {}
        concentration_risk = []
        position_analysis = []
        hhi = 0.0
        
        avg_weight = 100.0 / len(holdings)
        
        for pos in calculated_positions:
            weight = (pos["value"] / total_value) * 100.0
            hhi += weight ** 2
            
            # Sector exposure accumulation
            sector = pos["sector"]
            sector_totals[sector] = sector_totals.get(sector, 0.0) + weight
            
            # Concentration check
            is_concentrated = weight > 30.0
            concentration_risk.append({
                "symbol": pos["symbol"],
                "weight_percent": round(weight, 2),
                "value": round(pos["value"], 2),
                "is_high_concentration": is_concentrated
            })
            
            # Overweight analysis
            # Position is overweight if it exceeds 2x the average weight and represents > 20% of the portfolio
            is_overweight = weight > (avg_weight * 2.0) and weight > 20.0
            position_analysis.append({
                "symbol": pos["symbol"],
                "weight_percent": round(weight, 2),
                "is_overweight": is_overweight,
                "avg_weight_percent": round(avg_weight, 2),
                "status": "OVERWEIGHT" if is_overweight else "NORMAL"
            })
            
        # Round sector exposure values
        sector_exposure = {sec: round(val, 2) for sec, val in sector_totals.items()}
        
        # 3. Calculate Diversification Score based on HHI
        # HHI ranges from (100/N) to 10000 (totally concentrated).
        # We scale this to a 0 - 100 score.
        diversification_score = max(0.0, min(100.0, 100.0 - (hhi / 100.0)))
        
        return {
            "total_value": round(total_value, 2),
            "holdings_count": len(holdings),
            "sector_exposure": sector_exposure,
            "concentration_risk": sorted(concentration_risk, key=lambda x: x["weight_percent"], reverse=True),
            "diversification_score": round(diversification_score, 2),
            "position_analysis": position_analysis
        }

# Singleton instance
portfolio_risk_service = PortfolioRiskService()
