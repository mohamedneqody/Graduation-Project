import asyncio
import os
import csv
from dotenv import load_dotenv

load_dotenv()

async def seed_from_csv():
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    from app.database.session import AsyncSessionLocal
    from app.domains.drug.service import create_drug
    from app.domains.drug.schemas import DrugCreate
    
    csv_path = os.path.join(os.path.dirname(__file__), "..", "seed_data", "final_drugs_sheet.csv")
    
    added_count = 0
    async with AsyncSessionLocal() as db:
        # Clear existing drugs
        print("Clearing existing drugs table...")
        from sqlalchemy import text
        await db.execute(text("TRUNCATE TABLE drugs CASCADE;"))
        await db.commit()
        
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if len(rows) < 150:
                print(f"\n[WARNING] Found {len(rows)} drugs in file, which is less than the target (150).")
                print("Will only insert available drugs to ensure data correctness.\n")

            for row in rows:
                try:
                    # Clean and parse data
                    is_chronic_bool = str(row["is_chronic"]).lower().strip() == "true"
                    base_price = float(row["base_price"])
                    default_cycle_days = int(row["default_cycle_days"])
                    
                    drug_in = DrugCreate(
                        name=row["name"],
                        category=row["category"],
                        is_chronic=is_chronic_bool,
                        base_price=base_price,
                        default_cycle_days=default_cycle_days,
                        image_url=row["image_url"] if row["image_url"] else None
                    )
                    
                    db_drug = await create_drug(db, drug_in)
                    added_count += 1
                    print(f"[{added_count}] Successfully added: {db_drug.name}")
                except Exception as e:
                    print(f"Error adding {row.get('name')}: {e}")
                    
    print(f"\nSeed completed successfully. Inserted {added_count} real drugs into the database.")

if __name__ == "__main__":
    asyncio.run(seed_from_csv())
