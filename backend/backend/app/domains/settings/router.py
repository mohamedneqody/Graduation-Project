from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.dependencies.auth import require_role
from app.models.customer import Customer
from app.models.settings import TenantSettings
from . import schemas

router = APIRouter()

@router.get("/", response_model=schemas.TenantSettingsOut)
async def get_settings(
    current_user: Customer = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the tenant settings for the current user's tenant.
    Only admins (and super_admins) can access tenant settings.
    """
    result = await db.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == current_user.tenant_id)
    )
    settings = result.scalar_one_or_none()
    
    # If no settings exist yet, create defaults
    if not settings:
        settings = TenantSettings(tenant_id=current_user.tenant_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    return settings


@router.patch("/", response_model=schemas.TenantSettingsOut)
async def update_settings(
    settings_in: schemas.TenantSettingsUpdate,
    current_user: Customer = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the tenant settings for the current user's tenant.
    Only admins (and super_admins) can access tenant settings.
    """
    result = await db.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == current_user.tenant_id)
    )
    settings = result.scalar_one_or_none()
    
    # If no settings exist yet, create defaults first
    if not settings:
        settings = TenantSettings(tenant_id=current_user.tenant_id)
        db.add(settings)
    
    # Apply updates
    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
        
    await db.commit()
    await db.refresh(settings)
    
    return settings
