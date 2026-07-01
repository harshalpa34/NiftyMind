import pytest
import uuid

@pytest.mark.anyio
async def test_register_user_success(client):
    unique_id = uuid.uuid4().hex[:8]
    email = f"testuser_{unique_id}@niftymind.com"
    
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["full_name"] == "Test User"

@pytest.mark.anyio
async def test_register_user_duplicate_email(client):
    unique_id = uuid.uuid4().hex[:8]
    email = f"testuser_{unique_id}@niftymind.com"
    payload = {
        "email": email,
        "password": "password123",
        "full_name": "Test User"
    }
    
    # First registration
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201
    
    # Second registration with same email
    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409
    assert resp2.json()["message"] == "A user with this email already exists"

@pytest.mark.anyio
async def test_login_user_success(client):
    unique_id = uuid.uuid4().hex[:8]
    email = f"testuser_{unique_id}@niftymind.com"
    password = "securepassword123"
    
    # Register first
    resp_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Login Test User"
        }
    )
    assert resp_reg.status_code == 201
    
    # Log in
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email

@pytest.mark.anyio
async def test_login_user_invalid_credentials(client):
    unique_id = uuid.uuid4().hex[:8]
    email = f"testuser_{unique_id}@niftymind.com"
    
    # Register first
    resp_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Auth Failure User"
        }
    )
    assert resp_reg.status_code == 201
    
    # Try logging in with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["message"]
