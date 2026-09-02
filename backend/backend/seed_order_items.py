import asyncio
import os
import random
from uuid import UUID
import uuid
import logging
import argparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Get DB URL from env or use default
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")

async def seed_order_items(limit: int):
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    random.seed(os.environ.get("SEED_RANDOM_SEED", "42"))

    async with async_session() as session:
        async with session.begin():
            try:
                # Get some drugs
                result = await session.execute(text("SELECT drug_id, base_price FROM drugs LIMIT 50"))
                drugs = result.fetchall()
                
                if not drugs:
                    logger.info("No drugs found")
                    return
                    
                # Get some orders that have no items
                result = await session.execute(text("""
                    SELECT o.order_id 
                    FROM orders o
                    LEFT JOIN order_items oi ON o.order_id = oi.order_id
                    WHERE oi.order_item_id IS NULL
                    LIMIT :limit
                """), {"limit": limit})
                orders = result.fetchall()
                
                if not orders:
                    logger.info("All orders already have items or no orders exist")
                    return
                    
                logger.info(f"Found {len(orders)} orders without items. Seeding...")
                
                for order in orders:
                    num_items = random.randint(1, 3)
                    selected_drugs = random.sample(drugs, num_items)
                    
                    for drug in selected_drugs:
                        quantity = random.randint(1, 4)
                        # We use ON CONFLICT DO NOTHING assuming there might be a unique constraint
                        await session.execute(
                            text("""
                                INSERT INTO order_items (order_item_id, order_id, drug_id, quantity, price)
                                VALUES (:order_item_id, :order_id, :drug_id, :quantity, :price)
                                ON CONFLICT DO NOTHING
                            """),
                            {"order_item_id": str(uuid.uuid4()), "order_id": order[0], "drug_id": drug[0], "quantity": quantity, "price": drug[1]}
                        )
                
                logger.info("Successfully seeded order items!")
            except Exception as e:
                logger.exception("Seed failed. Transaction rolled back automatically.")
                raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed order items")
    parser.add_argument("--limit", type=int, default=100, help="Max number of orders to seed")
    args = parser.parse_args()
    
    asyncio.run(seed_order_items(limit=args.limit))
