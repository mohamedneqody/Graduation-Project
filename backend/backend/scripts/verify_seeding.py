import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.database.session import AsyncSessionLocal
from sqlalchemy import text

async def verify():
    async with AsyncSessionLocal() as db:
        # Check drugs count
        res = await db.execute(text("SELECT COUNT(*) FROM drugs"))
        drugs_count = res.scalar()
        print(f"Total drugs in DB: {drugs_count}")
        
        # Check categories
        print("\nCategories distribution:")
        res = await db.execute(text("SELECT category, COUNT(*) FROM drugs GROUP BY category ORDER BY count DESC"))
        for row in res.all():
            print(f"- {row[0]}: {row[1]}")
            
        # Check related tables
        tables = ['order_items', 'customer_cycles', 'drug_interactions', 'drug_affinities']
        print("\nRelated tables count (should be 0):")
        for t in tables:
            try:
                res = await db.execute(text(f"SELECT COUNT(*) FROM {t}"))
                print(f"- {t}: {res.scalar()}")
            except Exception as e:
                print(f"- {t}: Error (table might not exist yet) - {e}")

if __name__ == "__main__":
    asyncio.run(verify())
