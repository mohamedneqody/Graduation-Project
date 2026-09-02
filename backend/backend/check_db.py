import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text('SELECT count(*) FROM pending_reminders'))
        print('Pending Reminders Total:', res.scalar())
        res = await conn.execute(text("SELECT count(*) FROM pending_reminders WHERE status = 'pending'"))
        print('Pending Reminders (pending):', res.scalar())
        res = await conn.execute(text('SELECT count(*) FROM customers'))
        print('Customers:', res.scalar())
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
