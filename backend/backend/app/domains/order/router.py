from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import date
from app.database.session import get_db
from app.dependencies.auth import get_current_user, Customer
from . import schemas, service

router = APIRouter()

from app.models.session import Session
from app.dependencies.session import get_or_create_session
from app.domains.tracking.service import log_event
from app.domains.tracking.schemas import EventCreate

@router.post("/", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: schemas.OrderCreate,
    current_customer: Customer = Depends(get_current_user),
    session: Session = Depends(get_or_create_session),
    db: AsyncSession = Depends(get_db)
):
    order = await service.create_order(
        db=db,
        customer_id=current_customer.customer_id,
        tenant_id=current_customer.tenant_id,
        data=order_in
    )
    
    # Best-effort tracking
    try:
        await log_event(db, session.session_id, EventCreate(
            event_type="start_checkout",
            payload={"order_id": str(order.order_id), "total_amount": float(order.total_amount)}
        ))
    except Exception:
        pass
        
    return order

@router.get("/", response_model=schemas.PaginatedOrdersOut)
async def list_orders(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    current_customer: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.list_customer_orders(
        db=db,
        customer_id=current_customer.customer_id,
        tenant_id=current_customer.tenant_id,
        page=page,
        limit=limit,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to
    )

@router.get("/all", response_model=schemas.PaginatedOrdersOut)
async def list_all_orders(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
):
    return await service.list_all_orders(
        db=db,
        page=page,
        limit=limit,
        status_filter=status_filter
    )

@router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order(
    order_id: UUID = Path(...),
    current_customer: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.get_order(db, order_id, current_customer.customer_id, current_customer.tenant_id)

@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
async def update_order_status(
    status_update: schemas.OrderStatusUpdate,
    order_id: UUID = Path(...),
    current_customer: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await service.update_order_status(
        db=db,
        order_id=order_id,
        new_status=status_update.status,
        customer_id=current_customer.customer_id,
        tenant_id=current_customer.tenant_id
    )
