import pytest
from unittest.mock import AsyncMock, patch
from tests.api.test_portfolios import get_test_auth_headers

@pytest.mark.anyio
async def test_portfolio_summary_ai_advisor(client):
    headers = await get_test_auth_headers(client)
    
    # 1. Create a portfolio
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "AI Test Portfolio"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # Mock return value of generate_portfolio_summary to avoid live LLM calls during tests
    mock_summary = {
        "advisor_observations": "Your portfolio has tech exposure. Consider diversifying.",
        "corporate_highlights": "No critical corporate highlights."
    }
    
    # Patch the async generate_portfolio_summary function
    with patch("app.api.routes.advisor.portfolio_advisor.generate_portfolio_summary", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_summary
        
        # 2. Request AI portfolio summary
        response = await client.get(f"/api/v1/portfolio-summary/{portfolio_id}", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["portfolio_name"] == "AI Test Portfolio"
        assert data["ai_observations"] == "Your portfolio has tech exposure. Consider diversifying."
        assert data["corporate_highlights"] == "No critical corporate highlights."
        
        # 3. Assert mock was called
        mock_gen.assert_called_once()
