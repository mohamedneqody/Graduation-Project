import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def seed_pending_reminders():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        cust = await conn.execute(text("SELECT customer_id FROM customers LIMIT 1"))
        c_id = cust.scalar()
        drug = await conn.execute(text("SELECT drug_id FROM drugs LIMIT 1"))
        d_id = drug.scalar()
        
        if c_id and d_id:
            await conn.execute(text("""
                INSERT INTO pending_reminders (reminder_id, customer_id, drug_id, channel, decision, cycle_confidence, churn_probability, predicted_days, status)
                VALUES (gen_random_uuid(), :c_id, :d_id, 'whatsapp', 'auto_send', 0.9, 0.45, 30, 'pending')
            """), {"c_id": c_id, "d_id": d_id})
            print("Inserted a test reminder into pending_reminders")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_pending_reminders())
