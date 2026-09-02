import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.settings import TenantSettings
from app.models.customer import Customer
from app.models.tenant import Tenant

@pytest.mark.asyncio
async def test_get_settings_creates_default(
    async_client: AsyncClient,
    admin_token_headers: dict,
    db: AsyncSession,
    test_tenant: Tenant
):
    # Ensure no settings exist initially
    result = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == test_tenant.tenant_id))
    assert result.scalar_one_or_none() is None

    # Get settings (should create defaults)
    response = await async_client.get(
        "/api/v1/settings/",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ai_review_mode"] is True
    assert data["enterprise_notifications"] is False
    assert data["tenant_id"] == str(test_tenant.tenant_id)

    # Verify in DB
    result = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == test_tenant.tenant_id))
    settings = result.scalar_one_or_none()
    assert settings is not None
    assert settings.ai_review_mode is True

@pytest.mark.asyncio
async def test_update_settings(
    async_client: AsyncClient,
    admin_token_headers: dict,
    db: AsyncSession,
    test_tenant: Tenant
):
    # Update settings
    response = await async_client.patch(
        "/api/v1/settings/",
        headers=admin_token_headers,
        json={
            "ai_review_mode": False,
            "enterprise_notifications": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ai_review_mode"] is False
    assert data["enterprise_notifications"] is True

    # Verify in DB
    result = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == test_tenant.tenant_id))
    settings = result.scalar_one_or_none()
    assert settings.ai_review_mode is False
    assert settings.enterprise_notifications is True
