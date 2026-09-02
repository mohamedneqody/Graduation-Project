import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    res = await conn.fetch("SELECT tenant_id FROM tenants")
    print('Tenants:', [dict(r) for r in res])
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
