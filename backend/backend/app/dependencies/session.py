import uuid
from fastapi import Request, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.session import Session
from app.models.tenant import Tenant

async def get_or_create_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> Session:
    """
    Reads session_id from cookie. If missing or invalid, generates a new one.
    Sets the cookie on the response if a new one is generated.
    """
    session_id_str = request.cookies.get("session_id")
    session = None
    
    if session_id_str:
        try:
            session_uuid = uuid.UUID(session_id_str)
            result = await db.execute(select(Session).where(Session.session_id == session_uuid))
            session = result.scalars().first()
        except ValueError:
            pass # Invalid UUID format, treat as missing
            
    if not session:
        # We need a tenant_id. We'll fetch the first tenant for now or use a default
        # In a real multi-tenant setup, this comes from the domain/header
        tenant_result = await db.execute(select(Tenant).limit(1))
        tenant = tenant_result.scalars().first()
        tenant_id = tenant.tenant_id if tenant else uuid.uuid4() # Fallback if no tenants exist
        
        new_session_id = uuid.uuid4()
        user_agent = request.headers.get("user-agent", "")
        
        session = Session(
            session_id=new_session_id,
            tenant_id=tenant_id,
            customer_id=None, # Guest initially
            device_info=user_agent[:255] if user_agent else None
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Set cookie
        response.set_cookie(
            key="session_id",
            value=str(new_session_id),
            httponly=True,
            secure=True,  # Important for production
            samesite="lax",
            max_age=60*60*24*30 # 30 days
        )
        
    return session
