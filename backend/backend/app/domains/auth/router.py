from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from uuid import UUID

from app.database.session import get_db
from app.dependencies.auth import oauth2_scheme, verify_supabase_jwt
from app.models.customer import Customer
from app.domains.customer.schemas import CustomerOut
from app.models.session import Session
from app.dependencies.session import get_or_create_session
from app.domains.tracking.service import link_session_to_customer

router = APIRouter()

from app.models.tenant import Tenant

class RegistrationRequest(BaseModel):
    tenant_id: UUID | None = None
    full_name: str | None = None
    phone: str | None = None
    age_group: str | None = None
    preferred_channel: str = "whatsapp"
    preferred_language: str = "ar"

@router.post("/complete-registration", response_model=CustomerOut, status_code=status.HTTP_200_OK)
async def complete_registration(
    req: RegistrationRequest = RegistrationRequest(),
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_or_create_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Called by frontend immediately after a successful Supabase Signup/Login (Email or OAuth).
    Verifies JWT, extracts user info, and creates/updates local Customer record.
    """
    payload = await verify_supabase_jwt(token)
    auth_user_id = payload.get("sub")
    email = payload.get("email")
    user_metadata = payload.get("user_metadata") or {}
    
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")
        
    # 1. Check if customer already exists by auth_user_id
    result = await db.execute(select(Customer).where(Customer.auth_user_id == auth_user_id))
    customer = result.scalars().first()
    
    if customer:
        # Link existing session to the returning customer
        if session:
            await link_session_to_customer(db, session.session_id, customer.customer_id)
        return customer # Already registered
        
    # 2. Check if customer exists by email (link auth_user_id)
    if email:
        email_res = await db.execute(select(Customer).where(Customer.email == email))
        existing_by_email = email_res.scalars().first()
        if existing_by_email:
            existing_by_email.auth_user_id = auth_user_id
            await db.commit()
            await db.refresh(existing_by_email)
            if session:
                await link_session_to_customer(db, session.session_id, existing_by_email.customer_id)
            return existing_by_email

    # Need email from JWT for new customer
    if not email:
        raise HTTPException(status_code=400, detail="Token missing email. Cannot create customer.")
        
    # Resolve tenant_id
    target_tenant_id = req.tenant_id
    if not target_tenant_id:
        tenant_res = await db.execute(select(Tenant).where(Tenant.is_active == True))
        active_tenant = tenant_res.scalars().first()
        if not active_tenant:
            tenant_res = await db.execute(select(Tenant))
            active_tenant = tenant_res.scalars().first()
            
        if not active_tenant:
            raise HTTPException(status_code=404, detail="No active tenant found for customer registration")
        target_tenant_id = active_tenant.tenant_id

    resolved_name = req.full_name or user_metadata.get("full_name") or user_metadata.get("name") or email.split('@')[0]

    # Create new customer
    new_customer = Customer(
        auth_user_id=auth_user_id,
        tenant_id=target_tenant_id,
        email=email,
        full_name=resolved_name,
        phone=req.phone,
        age_group=req.age_group,
        preferred_channel=req.preferred_channel,
        preferred_language=req.preferred_language,
        is_active=True
    )
    
    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)
    
    # Link session to the newly created customer
    if session:
        await link_session_to_customer(db, session.session_id, new_customer.customer_id)
    
    return new_customer
