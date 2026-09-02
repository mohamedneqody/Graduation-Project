import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        try:
            res = await db.execute(text("SELECT polname, pg_get_expr(polqual, polrelid) FROM pg_policy WHERE polrelid = 'customers'::regclass"))
            for row in res.all():
                print(f"Policy: {row[0]}, Expr: {row[1]}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
