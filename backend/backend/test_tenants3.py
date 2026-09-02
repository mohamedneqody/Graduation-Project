import asyncio
import sys
sys.path.append(r"D:\Graduation Project\backend\backend")
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT tenant_id FROM tenants WHERE tenant_id = '24cf6cad-7cde-4d94-9fed-25b69e85ac23'"))
        print("Tenant exists?", res.fetchone() is not None)

if __name__ == "__main__":
    asyncio.run(main())
