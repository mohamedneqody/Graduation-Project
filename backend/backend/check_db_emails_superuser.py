import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    # The pooler string is postgresql+asyncpg://aicos_app...
    # We will replace aicos_app.quhfheudhewxqmvxwjij with postgres.quhfheudhewxqmvxwjij
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    url = url.replace('aicos_app.quhfheudhewxqmvxwjij', 'postgres.quhfheudhewxqmvxwjij')
    conn = await asyncpg.connect(url)
    emails = await conn.fetch("SELECT email, full_name, phone FROM customers")
    print("All Customers in DB (Bypassing RLS):")
    for e in emails:
        print(f"Name: {e['full_name']}, Email: {e['email']}, Phone: {e['phone']}")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
