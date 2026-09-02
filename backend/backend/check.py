import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010184333028686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    async with engine.connect() as conn:
        res2 = await conn.execute(text("SELECT name, image_url FROM drugs WHERE name ILIKE '%alerid%'"))
        row = res2.fetchone()
        print(repr(row[0]), repr(row[1]))

asyncio.run(main())
