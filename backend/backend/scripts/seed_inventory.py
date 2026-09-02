import asyncio
import uuid
import random
from sqlalchemy import text

from app.database.session import engine

async def seed_inventory():
    async with engine.begin() as conn:
        # Get all tenants
        result = await conn.execute(text("SELECT tenant_id FROM tenants"))
        tenants = result.fetchall()
        
        if not tenants:
            print("No tenants found to seed inventory.")
            return

        # Get all drugs
        result = await conn.execute(text("SELECT drug_id FROM drugs"))
        drugs = result.fetchall()

        if not drugs:
            print("No drugs found. Please run seed_drugs.py first.")
            return

        print(f"Found {len(tenants)} tenants and {len(drugs)} drugs.")

        # Clear existing inventory items to avoid duplicates on re-run
        await conn.execute(text("TRUNCATE TABLE inventory_items CASCADE"))
        print("Cleared existing inventory_items.")

        insert_query = text("""
            INSERT INTO inventory_items (inventory_id, tenant_id, drug_id, stock_level, reorder_point, tenant_price, is_active)
            VALUES (:inv_id, :tenant_id, :drug_id, :stock_level, :reorder_point, :tenant_price, :is_active)
        """)

        # Insert for each tenant
        for tenant in tenants:
            tid = tenant.tenant_id
            count = 0
            for drug in drugs:
                # Add ALL 114 drugs to every pharmacy
                await conn.execute(insert_query, {
                    "inv_id": uuid.uuid4(),
                    "tenant_id": tid,
                    "drug_id": drug.drug_id,
                    "stock_level": random.randint(10, 100),
                    "reorder_point": random.randint(5, 20),
                    "tenant_price": None, # Use base_price
                    "is_active": True
                })
                count += 1
            print(f"Seeded {count} inventory items for tenant {tid}")

        print("Inventory seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_inventory())
