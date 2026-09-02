import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_conn():
    # Trying eu-central-1
    url = "postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010184333028686@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Connection eu-central-1 successful:", result.scalar())
    except Exception as e:
        print("Connection eu-central-1 failed:", type(e).__name__, e)

    # Trying us-east-1
    url2 = "postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010184333028686@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    engine2 = create_async_engine(url2)
    try:
        async with engine2.connect() as conn2:
            result2 = await conn2.execute(text("SELECT 1"))
            print("Connection us-east-1 successful:", result2.scalar())
    except Exception as e:
        print("Connection us-east-1 failed:", type(e).__name__, e)

if __name__ == "__main__":
    asyncio.run(test_conn())
