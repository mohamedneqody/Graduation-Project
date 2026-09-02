import asyncio
import sys
sys.path.append(r"D:\Graduation Project\backend\backend")
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name = 'tenants'"))
        rows = res.fetchall()
        for r in rows:
            print(f"{r[0]}: {r[1]} ({r[2]})")

if __name__ == "__main__":
    asyncio.run(main())
