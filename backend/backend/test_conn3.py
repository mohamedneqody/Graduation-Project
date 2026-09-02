import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_conn():
    # Trying eu-central-1 port 5432 (Session pooler)
    url = "postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010184333028686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Connection 5432 successful:", result.scalar())
    except Exception as e:
        print("Connection 5432 failed:", type(e).__name__, e)

if __name__ == "__main__":
    asyncio.run(test_conn())
