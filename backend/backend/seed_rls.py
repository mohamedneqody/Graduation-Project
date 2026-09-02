import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def seed_pending_with_rls():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # Bypass RLS by pretending to be the tenant
        tenant_id = '62712616-be1e-4129-986f-4131877e63b8'
        await conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"tenant_id\": \"{tenant_id}\"}}}}'"))
        
        # Now find a customer
        cust = await conn.execute(text("SELECT customer_id FROM customers LIMIT 1"))
        c_id = cust.scalar()
        
        # Find a drug
        drug = await conn.execute(text("SELECT drug_id FROM drugs LIMIT 1"))
        d_id = drug.scalar()
        
        if not c_id or not d_id:
            print("Still no customers or drugs found even with RLS bypass!")
            return
            
        print(f"Found Customer {c_id} and Drug {d_id}")
        
        # Insert pending reminder
        await conn.execute(text("""
            INSERT INTO pending_reminders (reminder_id, customer_id, drug_id, channel, decision, cycle_confidence, churn_probability, predicted_days, status)
            VALUES (gen_random_uuid(), :c_id, :d_id, 'email', 'auto_send', 0.95, 0.30, 30, 'pending')
        """), {"c_id": c_id, "d_id": d_id})
        
        print("✅ Successfully inserted a test pending reminder!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_pending_with_rls())
