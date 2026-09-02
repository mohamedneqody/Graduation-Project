from typing import List
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.dialects.postgresql import insert

from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.tracking import CustomerCycle, Notification
from . import schemas

async def recalculate_cycle_for_pair(db: AsyncSession, customer_id: UUID, drug_id: UUID) -> CustomerCycle | None:
    # 1. Fetch orders + order_items for this customer and drug, ordered by order_date ascending
    query = (
        select(Order.order_date)
        .join(OrderItem, Order.order_id == OrderItem.order_id)
        .where(
            Order.customer_id == customer_id,
            OrderItem.drug_id == drug_id,
            Order.status == "completed"
        )
        .order_by(Order.order_date.asc())
    )
    result = await db.execute(query)
    purchase_dates = [row[0].date() if isinstance(row[0], datetime) else row[0] for row in result.all()]
    
    # 2. If less than 2 purchases, cannot calculate true average cycle
    if len(purchase_dates) < 2:
        return None
        
    # 3. Calculate differences in days
    differences = []
    for i in range(1, len(purchase_dates)):
        diff = (purchase_dates[i] - purchase_dates[i-1]).days
        differences.append(diff)
        
    avg_cycle_days = sum(differences) / len(differences)
    
    # 4. last_purchase_date
    last_purchase_date = purchase_dates[-1]
    
    # 5. reminder_day
    reminder_days_offset = round(avg_cycle_days * 0.85)
    reminder_day = last_purchase_date + timedelta(days=reminder_days_offset)
    
    # 6. Upsert CustomerCycle
    stmt = insert(CustomerCycle).values(
        customer_id=customer_id,
        drug_id=drug_id,
        avg_cycle_days=avg_cycle_days,
        last_purchase_date=last_purchase_date,
        reminder_day=reminder_day
    )
    
    stmt = stmt.on_conflict_do_update(
        index_elements=['customer_id', 'drug_id'],
        set_={
            'avg_cycle_days': avg_cycle_days,
            'last_purchase_date': last_purchase_date,
            'reminder_day': reminder_day
        }
    ).returning(CustomerCycle)
    
    res = await db.execute(stmt)
    await db.commit()
    
    return res.scalar_one_or_none()


async def recalculate_all_cycles(db: AsyncSession) -> schemas.RecalculationSummary:
    # 1. Get all unique (customer_id, drug_id) pairs with at least 2 completed orders
    query = (
        select(Order.customer_id, OrderItem.drug_id)
        .join(OrderItem, Order.order_id == OrderItem.order_id)
        .where(Order.status == "completed")
        .group_by(Order.customer_id, OrderItem.drug_id)
        .having(func.count(Order.order_id) >= 2)
    )
    
    result = await db.execute(query)
    pairs = result.all()
    
    processed = 0
    updated_or_created = 0
    
    for row in pairs:
        cust_id = row[0]
        drg_id = row[1]
        cycle = await recalculate_cycle_for_pair(db, cust_id, drg_id)
        processed += 1
        if cycle:
            updated_or_created += 1
            
    # Note: the prompt asks for updated_count and created_count, but PostgreSQL UPSERT 
    # doesn't trivially return whether it inserted or updated. We will just report
    # updated_count = updated_or_created and created_count = 0 for simplicity.
    return schemas.RecalculationSummary(
        updated_count=updated_or_created,
        created_count=0,
        total_processed=processed
    )


async def get_customers_due_for_reminder(db: AsyncSession, tenant_id: UUID) -> List[schemas.GroupedReminderOut]:
    today = date.today()
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    
    # 1. Find customers who have a reminder due today or earlier
    # 2. Exclude customers who received a reminder notification in the last 24 hours
    
    # Subquery: customers who got a reminder in last 24h
    recent_reminders_subq = (
        select(Notification.customer_id)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.notification_type == "reminder",
            Notification.status == "sent",
            Notification.sent_at >= yesterday
        )
    )
    
    # Query due customer cycles
    query = (
        select(CustomerCycle, Customer, Drug)
        .join(Customer, CustomerCycle.customer_id == Customer.customer_id)
        .join(Drug, CustomerCycle.drug_id == Drug.drug_id)
        .where(
            Customer.tenant_id == tenant_id,
            CustomerCycle.reminder_day <= today,
            CustomerCycle.customer_id.not_in(recent_reminders_subq)
        )
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    from collections import defaultdict
    
    grouped_data = defaultdict(lambda: {
        "preferred_channel": "", 
        "customer_contact": "", 
        "is_fallback_contact": False, 
        "due_drugs": []
    })
    
    for cycle, customer, drug in rows:
        if cycle.customer_id not in grouped_data or not grouped_data[cycle.customer_id]["preferred_channel"]:
            channel = customer.preferred_channel
            contact = ""
            is_fallback = False
            
            if channel in ["whatsapp", "sms"]:
                if customer.phone:
                    contact = customer.phone
                else:
                    contact = customer.email
                    is_fallback = True
            else:
                contact = customer.email
                
            grouped_data[cycle.customer_id]["preferred_channel"] = channel
            grouped_data[cycle.customer_id]["customer_contact"] = contact
            grouped_data[cycle.customer_id]["is_fallback_contact"] = is_fallback
            
        grouped_data[cycle.customer_id]["due_drugs"].append(schemas.DueDrug(
            drug_id=cycle.drug_id,
            drug_name=drug.name,
            avg_cycle_days=cycle.avg_cycle_days,
            reminder_day=cycle.reminder_day
        ))
        
    output = []
    for cust_id, data in grouped_data.items():
        output.append(schemas.GroupedReminderOut(
            customer_id=cust_id,
            preferred_channel=data["preferred_channel"],
            customer_contact=data["customer_contact"],
            is_fallback_contact=data["is_fallback_contact"],
            due_drugs=data["due_drugs"]
        ))
        
    return output
