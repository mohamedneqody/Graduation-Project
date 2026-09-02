import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def reset_reminders():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        result = await conn.execute(text("UPDATE pending_reminders SET status = 'pending' WHERE status = 'sent'"))
        print("Reset reminders back to 'pending' state.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_reminders())
