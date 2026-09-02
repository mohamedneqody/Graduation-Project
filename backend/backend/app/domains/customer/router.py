from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from app.database.session import get_db
from app.core.exceptions import NotFoundError
from app.dependencies.auth import get_current_user
from . import schemas, service

router = APIRouter()


class PaginatedCustomersResponse(BaseModel):
    items: List[schemas.CustomerOut]
    total: int
    page: int
    limit: int


@router.get("/health", response_model=schemas.HealthCheckOut)
async def health_check(db: AsyncSession = Depends(get_db)):
    return await service.check_health(db)


@router.post("/", response_model=schemas.CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: schemas.CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    return await service.create_customer(db, customer_in)


@router.get("/", response_model=PaginatedCustomersResponse)
async def list_customers(
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    page = (skip // limit) + 1
    items, total = await service.get_customers(
        db,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
        search=search,
    )
    return PaginatedCustomersResponse(items=items, total=total, page=page, limit=limit)


@router.get("/me", response_model=schemas.CustomerOut)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


class ContactMessageRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    message: str = ""

@router.post("/contact")
async def submit_contact(request: ContactMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Saves a contact message directly into the contact_messages table.
    Restored from older version to fix the broken contact us page.
    """
    from sqlalchemy import text
    from fastapi import HTTPException
    try:
        # Default tenant ID for the demo if not specified by user
        tenant_id = "62712616-be1e-4129-986f-4131877e63b8" 
        
        query = text("""
            INSERT INTO contact_messages (tenant_id, first_name, last_name, email, message)
            VALUES (:tenant_id, :first_name, :last_name, :email, :message)
        """)
        await db.execute(query, {
            "tenant_id": tenant_id,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "email": request.email,
            "message": request.message
        })
        await db.commit()
        return {"status": "success", "message": "Message saved"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contact/admin-inbox")
async def get_contact_messages(db: AsyncSession = Depends(get_db)):
    """
    Returns the latest contact messages for the admin dashboard notifications.
    """
    from sqlalchemy import text
    from fastapi import HTTPException
    try:
        query = text("""
            SELECT id, first_name, last_name, email, message, created_at
            FROM contact_messages
            ORDER BY created_at DESC
            LIMIT 20
        """)
        result = await db.execute(query)
        rows = result.fetchall()
        
        messages = []
        for r in rows:
            messages.append({
                "id": str(r[0]),
                "name": f"{r[1]} {r[2]}".strip(),
                "email": r[3],
                "message": r[4],
                "created_at": r[5].isoformat() if r[5] else None
            })
        return {"items": messages, "total": len(messages)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
async def get_customer(
    customer_id: UUID = Path(..., description="The UUID of the customer"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.get_customer(db, customer_id=customer_id, tenant_id=current_user.tenant_id)
