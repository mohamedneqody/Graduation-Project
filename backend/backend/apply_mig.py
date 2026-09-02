import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres.quhfheudhewxqmvxwjij:010704613318686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    async with engine.begin() as conn:
        sql = open(r'D:\Graduation Project\backend\supabase\migrations\20260810204435_create_contact_messages.sql', encoding='utf-8').read()
        for statement in sql.split(';'):
            if statement.strip():
                await conn.execute(text(statement))
    print('Migration applied successfully.')

if __name__ == "__main__":
    asyncio.run(main())
