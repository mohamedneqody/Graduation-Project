import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def seed_fake():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        tenant_id = '62712616-be1e-4129-986f-4131877e63b8'
        # Set context to bypass RLS for this tenant
        await conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"tenant_id\": \"{tenant_id}\"}}}}'"))
        
        # Create a fake customer
        c_id = "22222222-2222-2222-2222-222222222222"
        await conn.execute(text("""
            INSERT INTO customers (customer_id, tenant_id, full_name, email, phone) 
            VALUES (:c_id, :t_id, 'Test Customer n8n', 'test@test.com', '01000000000')
            ON CONFLICT (customer_id) DO NOTHING
        """), {"c_id": c_id, "t_id": tenant_id})
        
        # Find a real drug instead of inserting one
        drug = await conn.execute(text("SELECT drug_id FROM drugs LIMIT 1"))
        d_id = drug.scalar()
        
        if not d_id:
            print("No drugs found in database!")
            return
            
        # Delete old fake pending reminders if any
        await conn.execute(text("DELETE FROM pending_reminders WHERE customer_id = :c_id"), {"c_id": c_id})
        
        # Insert a fake pending reminder
        await conn.execute(text("""
            INSERT INTO pending_reminders (reminder_id, customer_id, drug_id, channel, decision, cycle_confidence, churn_probability, predicted_days, status)
            VALUES (gen_random_uuid(), :c_id, :d_id, 'email', 'auto_send', 0.9, 0.45, 30, 'pending')
        """), {"c_id": c_id, "d_id": d_id})
        
        print("✅ Successfully inserted a fully fake test reminder for n8n!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_fake())
