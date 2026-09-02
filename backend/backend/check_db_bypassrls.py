import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    res = await conn.fetch("SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    print(dict(res[0]))
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
