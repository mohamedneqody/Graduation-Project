from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from fastapi import HTTPException
from app.models.tracking import Notification
from app.models.customer import Customer
from . import schemas

async def check_health(db: AsyncSession) -> dict:
    return {"status": "ok"}

async def record_notification(db: AsyncSession, record_in: schemas.NotificationRecordIn) -> dict:
    # 1. Look up the customer to get tenant_id
    customer = (await db.execute(select(Customer).where(Customer.customer_id == record_in.customer_id))).scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    sent_at = datetime.now(timezone.utc) if record_in.status == "sent" else None
    
    # 2. Insert Notification
    notification = Notification(
        tenant_id=customer.tenant_id,
        customer_id=record_in.customer_id,
        notification_type=record_in.notification_type,
        channel=record_in.channel,
        ab_variant=record_in.ab_variant,
        status=record_in.status,
        sent_at=sent_at
    )
    
    db.add(notification)
    await db.commit()
    
    return {"status": "success", "notification_id": str(notification.notification_id)}
