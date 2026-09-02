import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check_query():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # Run the exact query used by get_pending_reminders
        query = text("""
            SELECT
                pr.reminder_id,
                pr.customer_id,
                c.full_name  AS customer_name,
                c.phone      AS customer_phone,
                c.email      AS customer_email,
                pr.drug_id,
                d.name       AS drug_name,
                pr.channel,
                pr.decision,
                pr.status
            FROM pending_reminders pr
            JOIN customers c ON c.customer_id = pr.customer_id
            JOIN drugs     d ON d.drug_id     = pr.drug_id
            WHERE pr.status = 'pending'
            LIMIT 10
        """)
        res = await conn.execute(query)
        rows = res.all()
        print(f"Query returned {len(rows)} rows.")
        for r in rows:
            print(dict(r._mapping))
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_query())
