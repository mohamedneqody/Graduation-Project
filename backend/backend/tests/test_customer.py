import pytest
from httpx import AsyncClient
import uuid

import pytest_asyncio

@pytest_asyncio.fixture
async def sample_tenant():
    from app.models.tenant import Tenant
    from tests.conftest import TestingSessionLocal
    
    async with TestingSessionLocal() as session:
        import uuid
        tenant = Tenant(
            name="Test Pharmacy",
            subdomain=f"testpharmacy_{uuid.uuid4().hex[:8]}",
            is_active=True
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        return tenant

@pytest.mark.asyncio
async def test_create_customer(async_client: AsyncClient, sample_tenant):
    payload = {
        "email": "customer@example.com",
        "full_name": "Test Customer",
        "phone": "+201234567890",
        "age_group": "adult",
        "preferred_channel": "email",
        "preferred_language": "ar",
        "auth_user_id": str(uuid.uuid4()),
        "tenant_id": str(sample_tenant.tenant_id)
    }
    
    response = await async_client.post("/api/v1/customers/", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "customer@example.com"
    assert "customer_id" in data
    
    return data

@pytest.mark.asyncio
async def test_list_customers(async_client: AsyncClient, sample_tenant):
    # Setup test by creating a customer
    payload = {
        "email": "customer2@example.com",
        "full_name": "Test Customer 2",
        "phone": "+201234567891",
        "age_group": "adult",
        "preferred_channel": "email",
        "preferred_language": "en",
        "auth_user_id": str(uuid.uuid4()),
        "tenant_id": str(sample_tenant.tenant_id)
    }
    await async_client.post("/api/v1/customers/", json=payload)
    
    # List customers
    response = await async_client.get("/api/v1/customers/")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) >= 1
    assert data[0]["email"] is not None

@pytest.mark.asyncio
async def test_get_customer(async_client: AsyncClient, sample_tenant):
    # Setup test by creating a customer
    payload = {
        "email": "customer3@example.com",
        "full_name": "Test Customer 3",
        "phone": "+201234567892",
        "auth_user_id": str(uuid.uuid4()),
        "tenant_id": str(sample_tenant.tenant_id)
    }
    create_resp = await async_client.post("/api/v1/customers/", json=payload)
    customer_id = create_resp.json()["customer_id"]
    
    # Get specific customer
    response = await async_client.get(f"/api/v1/customers/{customer_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["customer_id"] == customer_id
    assert data["email"] == "customer3@example.com"
