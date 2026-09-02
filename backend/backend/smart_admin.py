import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        try:
            # Disable RLS temporarily to bypass policy checks
            await db.execute(text("ALTER TABLE customers DISABLE ROW LEVEL SECURITY"))
            
            # Perform the update
            res = await db.execute(text("UPDATE customers SET role = 'admin' WHERE email = 'mohameb.eslam460@gmail.com' RETURNING email, role"))
            
            # Re-enable RLS
            await db.execute(text("ALTER TABLE customers ENABLE ROW LEVEL SECURITY"))
            
            await db.commit()
            row = res.first()
            if row:
                print(f"Updated successfully! Email: {row[0]}, Role: {row[1]}")
            else:
                print("No rows updated")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
