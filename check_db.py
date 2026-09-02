import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010704613318686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

async def check_db():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT status, error_message, raw_response, created_at FROM prescription_analyses ORDER BY created_at DESC LIMIT 3"))
        rows = result.fetchall()
        for row in rows:
            print(f"Time: {row.created_at}")
            print(f"Status: {row.status}")
            print(f"Error: {row.error_message}")
            if row.raw_response:
                print(f"Raw Response: {row.raw_response}")
            print("-" * 20)
            
asyncio.run(check_db())
