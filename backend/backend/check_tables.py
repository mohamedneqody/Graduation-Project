import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010704613318686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"))
        tables = result.fetchall()
        print('Tables in public schema:')
        for t in tables:
            print('-', t[0])

asyncio.run(main())
