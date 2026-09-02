import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    emails = await conn.fetch("SELECT email FROM customers")
    print("All Emails in DB:")
    for e in emails:
        print(e['email'])
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
