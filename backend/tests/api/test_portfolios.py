import pytest
import uuid

# Helper to register and login a test user to get headers
async def get_test_auth_headers(client):
    unique_id = uuid.uuid4().hex[:8]
    email = f"testuser_{unique_id}@niftymind.com"
    password = "password123"
    
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Portfolio Test User"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}

@pytest.mark.anyio
async def test_create_portfolio(client):
    headers = await get_test_auth_headers(client)
    
    response = await client.post(
        "/api/v1/portfolios",
        headers=headers,
        json={"name": "Tech Investments"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Tech Investments"

@pytest.mark.anyio
async def test_list_portfolios(client):
    headers = await get_test_auth_headers(client)
    
    # Create two portfolios
    await client.post("/api/v1/portfolios", headers=headers, json={"name": "Port A"})
    await client.post("/api/v1/portfolios", headers=headers, json={"name": "Port B"})
    
    response = await client.get("/api/v1/portfolios", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    names = {p["name"] for p in data}
    assert "Port A" in names
    assert "Port B" in names

@pytest.mark.anyio
async def test_portfolio_transactions_and_holdings_calculation(client):
    headers = await get_test_auth_headers(client)
    
    # 1. Create a portfolio
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "Equity Portfolio"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # 2. Record a BUY transaction: 10 units at 100.0 each
    r_buy1 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": "AAPL",
            "quantity": 10.0,
            "price": 100.0,
            "transaction_type": "BUY"
        }
    )
    assert r_buy1.status_code == 201
    
    # 3. Verify holdings: quantity should be 10, average price should be 100.0
    r_details1 = await client.get(f"/api/v1/portfolios/{portfolio_id}", headers=headers)
    assert r_details1.status_code == 200
    holdings1 = r_details1.json()["holdings"]
    assert len(holdings1) == 1
    assert holdings1[0]["symbol"] == "AAPL"
    assert float(holdings1[0]["quantity"]) == 10.0
    assert float(holdings1[0]["average_buy_price"]) == 100.0
    
    # 4. Record a second BUY transaction: 10 units at 200.0 each (average price should become 150.0)
    r_buy2 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": "AAPL",
            "quantity": 10.0,
            "price": 200.0,
            "transaction_type": "BUY"
        }
    )
    assert r_buy2.status_code == 201
    
    # 5. Verify holdings: quantity should be 20, average price should be 150.0
    r_details2 = await client.get(f"/api/v1/portfolios/{portfolio_id}", headers=headers)
    holdings2 = r_details2.json()["holdings"]
    assert float(holdings2[0]["quantity"]) == 20.0
    assert float(holdings2[0]["average_buy_price"]) == 150.0
    
    # 6. Record a SELL transaction: 15 units at 250.0 each (quantity should become 5, average cost unchanged)
    r_sell = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "symbol": "AAPL",
            "quantity": 15.0,
            "price": 250.0,
            "transaction_type": "SELL"
        }
    )
    assert r_sell.status_code == 201
    
    # 7. Verify holdings: quantity should be 5, average price remains 150.0
    r_details3 = await client.get(f"/api/v1/portfolios/{portfolio_id}", headers=headers)
    holdings3 = r_details3.json()["holdings"]
    assert float(holdings3[0]["quantity"]) == 5.0
    assert float(holdings3[0]["average_buy_price"]) == 150.0

@pytest.mark.anyio
async def test_delete_portfolio(client):
    headers = await get_test_auth_headers(client)
    
    # Create portfolio
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "To Delete"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # Delete it
    resp_del = await client.delete(f"/api/v1/portfolios/{portfolio_id}", headers=headers)
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "success"
    
    # Retrieve should fail with 404
    resp_get = await client.get(f"/api/v1/portfolios/{portfolio_id}", headers=headers)
    assert resp_get.status_code == 404

@pytest.mark.anyio
async def test_import_portfolio_csv(client):
    headers = await get_test_auth_headers(client)
    
    # 1. Create a portfolio
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "CSV Import Test"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # 2. Upload CSV content
    csv_data = "Symbol,Qty,Avg Cost\nRELIANCE,15,2450.50\nTCS,5,3100.00"
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/import",
        headers=headers,
        files={"file": ("portfolio.csv", csv_data, "text/csv")}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["imported_count"] == 2
    
    # 3. Retrieve portfolio and verify holdings
    resp_details = await client.get(f"/api/v1/portfolios/{portfolio_id}", headers=headers)
    assert resp_details.status_code == 200
    holdings = resp_details.json()["holdings"]
    assert len(holdings) == 2
    
    reliance = next(h for h in holdings if h["symbol"] == "RELIANCE")
    tcs = next(h for h in holdings if h["symbol"] == "TCS")
    
    assert float(reliance["quantity"]) == 15.0
    assert float(reliance["average_buy_price"]) == 2450.50
    assert float(tcs["quantity"]) == 5.0
    assert float(tcs["average_buy_price"]) == 3100.00

@pytest.mark.anyio
async def test_import_portfolio_excel(client):
    import io
    import openpyxl
    
    headers = await get_test_auth_headers(client)
    
    # 1. Create a portfolio
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "Excel Import Test"})
    assert resp_port.status_code == 201
    portfolio_id = resp_port.json()["id"]
    
    # 2. Generate Excel file in memory
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Ticker", "Shares", "Average Cost"])
    ws.append(["INFY", 50, 1600.25])
    ws.append(["HDFCBANK", 100, 1450.00])
    
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_content = excel_file.getvalue()
    
    # 3. Upload Excel
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/import",
        headers=headers,
        files={"file": ("portfolio.xlsx", excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["imported_count"] == 2
    
    # 4. Verify holdings
    resp_details = await client.get(f"/api/v1/portfolios/{portfolio_id}", headers=headers)
    holdings = resp_details.json()["holdings"]
    assert len(holdings) == 2
    
    infy = next(h for h in holdings if h["symbol"] == "INFY")
    hdfc = next(h for h in holdings if h["symbol"] == "HDFCBANK")
    
    assert float(infy["quantity"]) == 50.0
    assert float(infy["average_buy_price"]) == 1600.25
    assert float(hdfc["quantity"]) == 100.0
    assert float(hdfc["average_buy_price"]) == 1450.00

@pytest.mark.anyio
async def test_import_portfolio_invalid_headers(client):
    headers = await get_test_auth_headers(client)
    
    resp_port = await client.post("/api/v1/portfolios", headers=headers, json={"name": "Invalid Headers Test"})
    portfolio_id = resp_port.json()["id"]
    
    # Missing required 'Quantity' column
    csv_data = "Symbol,Avg Price\nRELIANCE,2450.50"
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/import",
        headers=headers,
        files={"file": ("portfolio.csv", csv_data, "text/csv")}
    )
    assert response.status_code == 400
    assert "Could not map file columns" in response.json()["message"]
