import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_conn():
    url = "postgresql+asyncpg://postgres:010184333028686@db.quhfheudhewxqmvxwjij.supabase.co:5432/postgres"
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Connection successful:", result.scalar())
    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    asyncio.run(test_conn())
