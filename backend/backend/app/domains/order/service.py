from uuid import UUID
from datetime import date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderItem
from app.models.drug import Drug
from app.models.customer import Customer
from app.models.tracking import AuditLog
from app.domains.drug.service import check_interactions
from app.core.exceptions import NotFoundError, BusinessRuleViolation, BadRequestError
from . import schemas

async def create_order(db: AsyncSession, customer_id: UUID, tenant_id: UUID, data: schemas.OrderCreate) -> schemas.OrderOut:
    # 1. Check if all drugs exist and get their prices
    requested_drug_ids = [item.drug_id for item in data.items]
    unique_drug_ids = list(set(requested_drug_ids))
    
    result = await db.execute(select(Drug).where(Drug.drug_id.in_(unique_drug_ids)))
    drugs = result.scalars().all()
    
    if len(drugs) != len(unique_drug_ids):
        found_ids = {drug.drug_id for drug in drugs}
        missing_ids = set(unique_drug_ids) - found_ids
        raise NotFoundError("Drug", str(missing_ids))
        
    drug_map = {drug.drug_id: drug for drug in drugs}
    
    # 2. Check for interactions
    warnings = []
    if len(unique_drug_ids) > 1:
        interactions = await check_interactions(db, unique_drug_ids)
        for interaction in interactions:
            drug_a_name = drug_map[interaction.drug_id_a].name
            drug_b_name = drug_map[interaction.drug_id_b].name
            msg = f"Interaction between {drug_a_name} and {drug_b_name}: {interaction.note}"
            
            if interaction.severity == "high":
                raise BusinessRuleViolation(
                    detail=f"Critical interaction detected: {msg}. Order cannot be processed."
                )
            else:
                warnings.append(f"[{interaction.severity.upper()}] {msg}")
                
    # 3. Create Order
    # We use a transaction block so everything succeeds or fails together
    async with db.begin_nested() if db.in_transaction() else db.begin():
        order = Order(
            tenant_id=tenant_id,
            customer_id=customer_id,
            status="completed", # Requirement 5: "completed" immediately for MVP
            channel=data.channel
        )
        db.add(order)
        await db.flush() # To get order_id
        
        # 4. Create OrderItems
        order_items_out = []
        total_amount = 0.0
        
        for item_in in data.items:
            drug = drug_map[item_in.drug_id]
            subtotal = float(drug.base_price) * item_in.quantity
            total_amount += subtotal
            
            order_item = OrderItem(
                order_id=order.order_id,
                drug_id=drug.drug_id,
                quantity=item_in.quantity,
                price=drug.base_price
            )
            db.add(order_item)
            await db.flush()
            
            order_items_out.append(
                schemas.OrderItemOut(
                    order_item_id=order_item.order_item_id,
                    drug_id=drug.drug_id,
                    drug_name=drug.name,
                    quantity=order_item.quantity,
                    price=float(order_item.price),
                    subtotal=subtotal
                )
            )
            
    await db.commit() # Commit transaction
    await db.refresh(order) # Refresh to get server defaults like order_date
    
    return schemas.OrderOut(
        order_id=order.order_id,
        order_date=order.order_date,
        status=order.status,
        channel=order.channel,
        items=order_items_out,
        total_amount=total_amount,
        warnings=warnings
    )

async def _build_order_out(
    db: AsyncSession,
    order: Order,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None
) -> schemas.OrderOut:
    """Helper to convert Order to OrderOut, loading necessary drug data."""
    # Fetch items and their drugs
    result = await db.execute(
        select(OrderItem, Drug)
        .join(Drug, OrderItem.drug_id == Drug.drug_id)
        .where(OrderItem.order_id == order.order_id)
    )
    rows = result.all()
    
    items_out = []
    total_amount = 0.0
    for order_item, drug in rows:
        subtotal = float(order_item.price) * order_item.quantity
        total_amount += subtotal
        items_out.append(
            schemas.OrderItemOut(
                order_item_id=order_item.order_item_id,
                drug_id=order_item.drug_id,
                drug_name=drug.name,
                quantity=order_item.quantity,
                price=float(order_item.price),
                subtotal=subtotal
            )
        )
        
    return schemas.OrderOut(
        order_id=order.order_id,
        order_date=order.order_date,
        status=order.status,
        channel=order.channel,
        items=items_out,
        total_amount=total_amount,
        warnings=[],  # Warnings are only generated during creation
        customer_name=customer_name,
        customer_email=customer_email,
    )

async def get_order(db: AsyncSession, order_id: UUID, customer_id: UUID, tenant_id: UUID) -> schemas.OrderOut:
    result = await db.execute(
        select(Order).where(Order.order_id == order_id)
    )
    order = result.scalars().first()
    
    # We return NotFoundError if the order doesn't exist OR if it belongs to another customer or tenant
    if not order or order.customer_id != customer_id or order.tenant_id != tenant_id:
        raise NotFoundError("Order", str(order_id))
        
    return await _build_order_out(db, order)

async def list_customer_orders(
    db: AsyncSession, 
    customer_id: UUID, 
    tenant_id: UUID,
    page: int, 
    limit: int, 
    status_filter: Optional[str] = None, 
    date_from: Optional[date] = None, 
    date_to: Optional[date] = None
) -> schemas.PaginatedOrdersOut:
    
    query = select(Order).where(Order.customer_id == customer_id, Order.tenant_id == tenant_id)
    
    if status_filter:
        query = query.where(Order.status == status_filter)
    if date_from:
        query = query.where(func.date(Order.order_date) >= date_from)
    if date_to:
        query = query.where(func.date(Order.order_date) <= date_to)
        
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Pagination
    offset = (page - 1) * limit
    query = query.order_by(desc(Order.order_date)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    # Build OrderOut for each
    order_outs = []
    for order in orders:
        order_outs.append(await _build_order_out(db, order))
        
    return schemas.PaginatedOrdersOut(
        items=order_outs,
        total=total,
        page=page,
        limit=limit
    )

async def list_all_orders(
    db: AsyncSession,
    tenant_id: Optional[UUID] = None,
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None
) -> schemas.PaginatedOrdersOut:
    # Build base query joining orders with customers
    query = (
        select(Order, Customer.full_name.label("cust_name"), Customer.email.label("cust_email"))
        .outerjoin(Customer, Order.customer_id == Customer.customer_id)
    )
    if tenant_id:
        query = query.where(Order.tenant_id == tenant_id)
    if status_filter and status_filter not in ("All Statuses", "all", ""):
        query = query.where(Order.status == status_filter.lower())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * limit
    query = query.order_by(desc(Order.order_date)).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        order = row[0]
        cust_name = row[1]
        cust_email = row[2]
        items.append(await _build_order_out(db, order, customer_name=cust_name, customer_email=cust_email))

    return schemas.PaginatedOrdersOut(
        items=items,
        total=total,
        page=page,
        limit=limit
    )


async def update_order_status(db: AsyncSession, order_id: UUID, new_status: str, customer_id: UUID, tenant_id: UUID) -> schemas.OrderOut:
    result = await db.execute(select(Order).where(Order.order_id == order_id))
    order = result.scalars().first()
    
    if not order or order.customer_id != customer_id or order.tenant_id != tenant_id:
        raise NotFoundError("Order", str(order_id))
        
    # State Machine Rules:
    # pending -> completed (allowed)
    # pending -> cancelled (allowed)
    # completed -> cancelled (allowed - for returns/refunds usually)
    # cancelled -> completed (forbidden - cannot resurrect a cancelled order)
    # cancelled -> pending (forbidden)
    # completed -> pending (forbidden)
    
    valid_transitions = {
        "pending": ["completed", "cancelled"],
        "completed": ["cancelled"],
        "cancelled": []
    }
    
    if order.status == new_status:
        return await _build_order_out(db, order)
        
    allowed_next_states = valid_transitions.get(order.status, [])
    
    if new_status not in allowed_next_states:
        raise BusinessRuleViolation(
            detail=f"Invalid status transition from '{order.status}' to '{new_status}'. Allowed transitions: {allowed_next_states}"
        )
        
    old_status = order.status
    order.status = new_status
    
    if old_status == "completed" and new_status == "cancelled":
        audit_log = AuditLog(
            tenant_id=order.tenant_id,
            actor_id=str(customer_id),
            action_type="order_cancelled_after_completion",
            target_entity=f"order:{order_id}"
        )
        db.add(audit_log)
        
    await db.commit()
    await db.refresh(order)
    
    return await _build_order_out(db, order)
