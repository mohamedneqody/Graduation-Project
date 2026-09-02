import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def seed_fake():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # Create a fake tenant
        tenant_id = "11111111-1111-1111-1111-111111111111"
        await conn.execute(text("""
            INSERT INTO tenants (tenant_id, name) 
            VALUES (:t_id, 'Test Tenant')
            ON CONFLICT (tenant_id) DO NOTHING
        """), {"t_id": tenant_id})
        
        # Create a fake customer
        c_id = "22222222-2222-2222-2222-222222222222"
        await conn.execute(text("""
            INSERT INTO customers (customer_id, tenant_id, name, email, phone) 
            VALUES (:c_id, :t_id, 'Test Customer', 'test@test.com', '01000000000')
            ON CONFLICT (customer_id) DO NOTHING
        """), {"c_id": c_id, "t_id": tenant_id})
        
        # Create a fake drug
        d_id = "33333333-3333-3333-3333-333333333333"
        await conn.execute(text("""
            INSERT INTO drugs (drug_id, tenant_id, name, base_price, is_chronic) 
            VALUES (:d_id, :t_id, 'Test Drug 10mg', 100.0, true)
            ON CONFLICT (drug_id) DO NOTHING
        """), {"d_id": d_id, "t_id": tenant_id})
        
        # Delete old fake pending reminders if any
        await conn.execute(text("DELETE FROM pending_reminders WHERE customer_id = :c_id"), {"c_id": c_id})
        
        # Insert a fake pending reminder with 45% churn (gets 15% discount)
        await conn.execute(text("""
            INSERT INTO pending_reminders (reminder_id, customer_id, drug_id, channel, decision, cycle_confidence, churn_probability, predicted_days, status)
            VALUES (gen_random_uuid(), :c_id, :d_id, 'email', 'auto_send', 0.9, 0.45, 30, 'pending')
        """), {"c_id": c_id, "d_id": d_id})
        
        print("✅ Successfully inserted a fully fake test reminder with Customer & Drug data!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_fake())
