import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.customer import Customer

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Customer))
        customers = res.scalars().all()
        print(f"Total customers: {len(customers)}")
        for c in customers:
            print(f"{c.email}: {c.role}")

asyncio.run(main())
