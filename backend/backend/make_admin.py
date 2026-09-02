import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        try:
            res = await db.execute(text("UPDATE customers SET role = 'admin' WHERE email = 'mohameb.eslam460@gmail.com' RETURNING email, role"))
            await db.commit()
            row = res.first()
            if row:
                print(f"Updated! Email: {row[0]}, Role: {row[1]}")
            else:
                print("No rows updated (RLS blocked or not found)")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
