import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env')
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    res = await conn.fetch("SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE conrelid = 'customers'::regclass")
    for r in res:
        print(dict(r))
    
    # Also check if the email exists
    emails = await conn.fetch("SELECT email FROM customers")
    print("Emails:", [e['email'] for e in emails])
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
