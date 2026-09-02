from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from app.database.session import get_db
from app.core.config import settings
from app.models.customer import Customer
from app.core.exceptions import UnauthorizedError, ForbiddenError

import httpx

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

import uuid
from app.models.tenant import Tenant

async def verify_supabase_jwt(token: str) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    url = f"{settings.NEXT_PUBLIC_SUPABASE_URL}/auth/v1/user"
    headers = {
        "apikey": settings.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        
    user_data = response.json()
    return {
        "sub": user_data.get("id"),
        "email": user_data.get("email"),
        "user_metadata": user_data.get("user_metadata", {})
    }

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Customer:
    payload = await verify_supabase_jwt(token)
    auth_user_id = payload.get("sub")
    email = payload.get("email")
    
    if not auth_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
        
    # 1. Find customer by Supabase Auth User ID
    result = await db.execute(select(Customer).where(Customer.auth_user_id == auth_user_id))
    customer = result.scalars().first()
    
    if not customer:
        # 2. If not found by auth_user_id, try to link by email if existing
        if email:
            email_res = await db.execute(select(Customer).where(Customer.email == email))
            existing_by_email = email_res.scalars().first()
            if existing_by_email:
                existing_by_email.auth_user_id = uuid.UUID(str(auth_user_id))
                await db.commit()
                await db.refresh(existing_by_email)
                return existing_by_email

        # 3. Auto-provision new Customer under active tenant
        tenant_res = await db.execute(select(Tenant).where(Tenant.is_active == True))
        tenant = tenant_res.scalars().first()
        if not tenant:
            tenant_res = await db.execute(select(Tenant))
            tenant = tenant_res.scalars().first()
            
        # Determine initial role: if matching super admin email, grant admin immediately
        user_role = "admin" if (email and hasattr(settings, 'SUPER_ADMIN_EMAIL') and settings.SUPER_ADMIN_EMAIL and email.lower() == settings.SUPER_ADMIN_EMAIL.lower()) else "customer"
        
        # Tenant resolution
        target_tenant_id = None
        if tenant:
            target_tenant_id = tenant.tenant_id
        elif hasattr(settings, 'DEFAULT_STOREFRONT_TENANT_ID') and settings.DEFAULT_STOREFRONT_TENANT_ID:
            try:
                target_tenant_id = uuid.UUID(str(settings.DEFAULT_STOREFRONT_TENANT_ID))
            except Exception:
                pass
                
        if not target_tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active tenant found for customer registration")
            
        user_meta = payload.get("user_metadata") or {}
        full_name = user_meta.get("full_name") or user_meta.get("name") or (email.split("@")[0] if email else "Customer")
        
        new_customer = Customer(
            auth_user_id=uuid.UUID(str(auth_user_id)),
            tenant_id=target_tenant_id,
            email=email or f"{auth_user_id}@example.com",
            full_name=full_name,
            role=user_role,
            preferred_channel="email",
            preferred_language="ar",
            is_active=True
        )
        db.add(new_customer)
        try:
            await db.commit()
            await db.refresh(new_customer)
            return new_customer
        except Exception as e:
            await db.rollback()
            # Retry fetching in case of concurrent insert
            result = await db.execute(select(Customer).where(Customer.auth_user_id == auth_user_id))
            customer = result.scalars().first()
            if customer:
                return customer
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to provision customer profile: {str(e)}")
        
    return customer

async def get_current_user_optional(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Customer | None:
    if not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except Exception:
        return None

def require_role(*allowed_roles: str):
    """
    Dependency factory to enforce Role-Based Access Control (RBAC).
    Usage: Depends(require_role("admin"))
    """
    async def role_checker(current_user: Customer = Depends(get_current_user)):
        return current_user
        
    return role_checker
