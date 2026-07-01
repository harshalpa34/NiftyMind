import pytest
import uuid
from tests.api.test_portfolios import get_test_auth_headers

@pytest.mark.anyio
async def test_risk_analysis_metrics(client):
    headers = await get_test_auth_headers(client)
    
    # 1. Create a portfolio
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "Tech/FMCG Portfolio"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # 2. Add BUY transaction for stock A (e.g. INFY)
    await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": "INFY",
            "quantity": 10.0,
            "price": 1500.0,
            "transaction_type": "BUY"
        }
    )
    
    # 3. Add BUY transaction for stock B (e.g. RELIANCE)
    await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": "RELIANCE",
            "quantity": 5.0,
            "price": 2400.0,
            "transaction_type": "BUY"
        }
    )
    
    # 4. Request risk analysis
    response = await client.get(f"/api/v1/risk-analysis/{portfolio_id}", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "total_value" in data
    assert "diversification_score" in data
    assert "sector_exposure" in data
    assert "concentration_risk" in data
    
    # Check that total value and score are correctly returned
    # Current prices are from MOCK_MARKET_PRICES: INFY = 1850.0, RELIANCE = 2450.0
    expected_total_value = (10 * 1850.0) + (5 * 2450.0)
    assert data["total_value"] == expected_total_value
    assert 0 <= data["diversification_score"] <= 100
