import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.drug import Drug

async def check_images():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Drug).where(Drug.name.in_(["Coldrex", "Comtrex"]))
        )
        drugs = result.scalars().all()
        for drug in drugs:
            print(f"Drug: {drug.name}, Image URL: {drug.image_url}")

if __name__ == "__main__":
    asyncio.run(check_images())
