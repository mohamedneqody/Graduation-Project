from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID
import logging

from app.models.customer import Customer
from app.models.order import Order
from app.core.exceptions import BadRequestError, NotFoundError
from . import schemas

logger = logging.getLogger(__name__)

async def check_health(db: AsyncSession) -> dict:
    return {"status": "ok"}

async def create_customer(db: AsyncSession, customer_in: schemas.CustomerCreate) -> Customer:
    try:
        db_customer = Customer(
            auth_user_id=customer_in.auth_user_id,
            tenant_id=customer_in.tenant_id,
            email=customer_in.email,
            full_name=customer_in.full_name,
            phone=customer_in.phone,
            age_group=customer_in.age_group,
            preferred_channel=customer_in.preferred_channel,
            preferred_language=customer_in.preferred_language
        )
        db.add(db_customer)
        await db.commit()
        await db.refresh(db_customer)
        return db_customer
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError in create_customer: {e}")
        raise BadRequestError("Customer with this email or auth_user_id already exists")


async def get_customers(
    db: AsyncSession,
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None
) -> tuple[List[schemas.CustomerOut], int]:
    """Return paginated customers with order count."""
    # Subquery: count orders per customer
    order_count_sq = (
        select(Order.customer_id, func.count(Order.order_id).label("total_orders"))
        .group_by(Order.customer_id)
        .subquery()
    )

    query = (
        select(Customer, func.coalesce(order_count_sq.c.total_orders, 0).label("total_orders"))
        .outerjoin(order_count_sq, Customer.customer_id == order_count_sq.c.customer_id)
        .where(Customer.tenant_id == tenant_id)
    )

    if search:
        pattern = f"%{search}%"
        query = query.where(
            Customer.full_name.ilike(pattern) | Customer.email.ilike(pattern)
        )

    # Total count (same filters as main query)
    count_base = select(Customer).where(Customer.tenant_id == tenant_id)
    if search:
        pattern = f"%{search}%"
        count_base = count_base.where(
            Customer.full_name.ilike(pattern) | Customer.email.ilike(pattern)
        )
    count_q = select(func.count()).select_from(count_base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Customer.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    out = []
    for row in rows:
        customer = row[0]
        order_count = row[1]
        customer_out = schemas.CustomerOut(
            customer_id=customer.customer_id,
            tenant_id=customer.tenant_id,
            email=customer.email,
            full_name=customer.full_name,
            phone=customer.phone,
            age_group=customer.age_group,
            preferred_channel=customer.preferred_channel,
            preferred_language=customer.preferred_language,
            is_active=customer.is_active,
            created_at=customer.created_at,
            last_login_at=customer.last_login_at,
            total_orders=order_count,
            role=getattr(customer, "role", None),
        )
        out.append(customer_out)

    return out, total


async def get_customer(db: AsyncSession, customer_id: UUID, tenant_id: UUID) -> Customer:
    result = await db.execute(
        select(Customer)
        .where(Customer.customer_id == customer_id, Customer.tenant_id == tenant_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise NotFoundError("Customer", str(customer_id))
    return customer
