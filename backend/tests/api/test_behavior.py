import pytest
import uuid
from datetime import datetime
from tests.api.test_portfolios import get_test_auth_headers

@pytest.mark.anyio
async def test_excessive_concentration_flag(client):
    headers = await get_test_auth_headers(client)
    
    # 1. Create a portfolio
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "Concentrated Portfolio"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # 2. Add a single stock holding (representing 100% of portfolio)
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
    
    # 3. Check behavioral flags
    response = await client.get(f"/api/v1/behavioral-analysis/{portfolio_id}", headers=headers)
    assert response.status_code == 200
    flags = response.json()
    
    # Verify concentration flag is triggered (> 30% threshold)
    concentration_flags = [f for f in flags if f["flag_type"] == "EXCESSIVE_CONCENTRATION"]
    assert len(concentration_flags) == 1
    assert "severity" in concentration_flags[0]
    assert "INFY" in concentration_flags[0]["description"]

@pytest.mark.anyio
async def test_overtrading_flag(client):
    headers = await get_test_auth_headers(client)
    
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "High Frequency Portfolio"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # Execute 6 transactions in rapid succession
    for i in range(3):
        # Buy INFY
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/transactions",
            headers=headers,
            json={
                "symbol": "INFY",
                "quantity": 1.0,
                "price": 1500.0,
                "transaction_type": "BUY"
            }
        )
        # Sell INFY
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/transactions",
            headers=headers,
            json={
                "symbol": "INFY",
                "quantity": 1.0,
                "price": 1500.0,
                "transaction_type": "SELL"
            }
        )
        
    response = await client.get(f"/api/v1/behavioral-analysis/{portfolio_id}", headers=headers)
    assert response.status_code == 200
    flags = response.json()
    
    overtrading_flags = [f for f in flags if f["flag_type"] == "OVERTRADING"]
    assert len(overtrading_flags) == 1

@pytest.mark.anyio
async def test_fomo_and_revenge_trading_flags(client):
    headers = await get_test_auth_headers(client)
    
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "Emotional Portfolio"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # 1. Buy INFY
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
    # 2. Sell INFY (loss/neutral)
    await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": "INFY",
            "quantity": 10.0,
            "price": 1500.0,
            "transaction_type": "SELL"
        }
    )
    # 3. Buy INFY back quickly with larger size (Revenge sizing: 2x quantity)
    await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": "INFY",
            "quantity": 20.0,
            "price": 1500.0,
            "transaction_type": "BUY"
        }
    )
    
    response = await client.get(f"/api/v1/behavioral-analysis/{portfolio_id}", headers=headers)
    assert response.status_code == 200
    flags = response.json()
    
    flag_types = {f["flag_type"] for f in flags}
    # Should flag REVENGE_TRADE or FOMO due to rapid re-entry
    assert "REVENGE_TRADE" in flag_types or "FOMO" in flag_types
