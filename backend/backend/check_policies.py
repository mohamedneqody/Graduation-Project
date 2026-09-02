import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    res = await conn.fetch("SELECT policyname, permissive, roles, cmd, qual, with_check FROM pg_policies WHERE tablename = 'customers'")
    print('Policies:')
    for r in res:
        print(dict(r))
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
