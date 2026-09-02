import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env')
    url = os.environ.get('DATABASE_URL')
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT email FROM customers"))
        emails = res.fetchall()
        print("Emails:", [e[0] for e in emails])
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
