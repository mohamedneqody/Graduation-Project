import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def get_tenant():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('SELECT tenant_id FROM tenants LIMIT 1'))
        row = result.first()
        if row:
            print(f'Tenant ID: {row[0]}')
        else:
            print('No tenant found.')

if __name__ == "__main__":
    asyncio.run(get_tenant())
