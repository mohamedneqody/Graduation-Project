import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_signup_success(async_client):
    response = await async_client.post(
        "/api/v1/auth/signup",
        json={
            "email": "test@example.com",
            "password": "strongpassword123",
            "full_name": "Test User",
            "role": "customer"
        }
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert "message" in data

@pytest.mark.asyncio
async def test_signup_duplicate_email(async_client):
    # Try to signup with the same email
    response = await async_client.post(
        "/api/v1/auth/signup",
        json={
            "email": "test@example.com",
            "password": "anotherpassword",
            "full_name": "Another User",
            "role": "customer"
        }
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "strongpassword123",
            "full_name": "Test User",
            "role": "customer"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword",
            "full_name": "Test User",
            "role": "customer"
        }
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_unauthorized(async_client):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_authorized(async_client):
    # 1. Login to get token
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "strongpassword123",
            "full_name": "Test User",
            "role": "customer"
        }
    )
    token = login_response.json()["access_token"]
    
    # 2. Use token to get profile
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data["current_user"]
