import asyncio
import sys
sys.path.append(r"D:\Graduation Project\backend\backend")
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM prescription_items"))
        await db.execute(text("DELETE FROM prescription_analyses"))
        await db.execute(text("DELETE FROM prescriptions"))
        await db.commit()
        print("Deleted all test prescriptions.")

if __name__ == "__main__":
    asyncio.run(main())
