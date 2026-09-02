from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import uuid

from app.database.session import get_db
from app.models.inventory import InventoryItem
from app.models.drug import Drug
from app.dependencies.auth import get_current_user_optional, get_current_user, require_role
from app.core.config import settings
from sqlalchemy import text

router = APIRouter(tags=["inventory"])

@router.get("/")
async def get_inventory(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional),
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get inventory items for the current tenant.
    RLS automatically filters to the user's tenant_id.
    """
    # If anonymous user, use the configured storefront tenant.
    # The value comes from settings.DEFAULT_STOREFRONT_TENANT_ID (env var),
    # never from a hardcoded string inside source code (C-02 fix).
    if current_user is None:
        target_tenant_id = settings.DEFAULT_STOREFRONT_TENANT_ID
        try:
            await db.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": target_tenant_id},
            )
        except Exception:
            pass
    else:
        target_tenant_id = current_user.tenant_id
            
    # Join InventoryItem with Drug to get drug details
    base_query = select(InventoryItem, Drug).join(Drug, InventoryItem.drug_id == Drug.drug_id).filter(InventoryItem.tenant_id == target_tenant_id)
    count_query = select(func.count()).select_from(InventoryItem).join(Drug, InventoryItem.drug_id == Drug.drug_id).filter(InventoryItem.tenant_id == target_tenant_id)
    
    if search:
        base_query = base_query.filter(Drug.name.ilike(f"%{search}%"))
        count_query = count_query.filter(Drug.name.ilike(f"%{search}%"))
        
    if category and category != "All":
        base_query = base_query.filter(Drug.category == category)
        count_query = count_query.filter(Drug.category == category)
        
    query = base_query.limit(limit).offset(offset)
    
    # Execute count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Execute query
    result = await db.execute(query)
    rows = result.all()
    
    inventory = []
    for inv, drug in rows:
        inventory.append({
            "inventory_id": inv.inventory_id,
            "drug_id": drug.drug_id,
            "name": drug.name,
            "category": drug.category,
            "is_chronic": drug.is_chronic,
            "stock_level": inv.stock_level,
            "price": float(inv.tenant_price) if inv.tenant_price is not None else float(drug.base_price),
            "image_url": drug.image_url,
            "is_active": inv.is_active
        })
        
    return {
        "items": inventory,
        "total": total,
        "page": (offset // limit) + 1 if limit > 0 else 1,
        "limit": limit
    }

@router.patch("/{inventory_id}")
async def update_inventory(
    inventory_id: uuid.UUID,
    stock_level: Optional[int] = None,
    tenant_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin", "pharmacist"))
):
    """Update stock level or price for a specific inventory item."""
    result = await db.execute(
        select(InventoryItem).filter(
            InventoryItem.inventory_id == inventory_id,
            InventoryItem.tenant_id == current_user.tenant_id
        )
    )
    inv = result.scalar_one_or_none()
    
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory item not found")
        
    if stock_level is not None:
        inv.stock_level = stock_level
    if tenant_price is not None:
        inv.tenant_price = tenant_price
        
    await db.commit()
    return {"message": "Inventory updated successfully"}
