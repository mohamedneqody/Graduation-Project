import asyncio
import sys
import os
sys.path.append(os.path.abspath('.'))
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.core.config import settings

async def reset_db():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with AsyncSession(engine) as session:
        result = await session.execute(text("UPDATE pending_reminders SET status = 'pending' RETURNING *"))
        rows = result.fetchall()
        await session.commit()
        print(f"Updated {len(rows)} rows to 'pending'")

asyncio.run(reset_db())
