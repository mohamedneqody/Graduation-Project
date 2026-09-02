import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env')
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    res = await conn.fetch("SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'customers'")
    print("RLS enabled?", dict(res[0]))
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
