import asyncio
import os
import shutil

async def fix_database():
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    from app.database.session import AsyncSessionLocal
    from sqlalchemy import text
    from app.domains.drug.service import create_drug
    from app.domains.drug.schemas import DrugCreate
    
    # Clean up local folders containing fake images
    images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drug_images"))
    if os.path.exists(images_dir):
        shutil.rmtree(images_dir)
        print("Deleted generated image directory.")
        
    async with AsyncSessionLocal() as db:
        # Wipe all existing drugs
        print("Truncating drugs table...")
        await db.execute(text("TRUNCATE TABLE drugs CASCADE"))
        await db.commit()
        
        # Test array with strictly matching categories and NO images
        drugs = [
            {
                "name": "Panadol Advance 500mg 24 Tablets",
                "category": "مسكنات",
                "is_chronic": False,
                "base_price": 40.0,
                "image_url": None,
                "default_cycle_days": 10
            },
            {
                "name": "Concor 5mg 30 Tablets",
                "category": "مزمن - ضغط",
                "is_chronic": True,
                "base_price": 58.0,
                "image_url": None,
                "default_cycle_days": 30
            },
            {
                "name": "Augmentin 1g 14 Tablets",
                "category": "مضاد حيوي",
                "is_chronic": False,
                "base_price": 115.0,
                "image_url": None,
                "default_cycle_days": 7
            },
            {
                "name": "Glucophage 1000mg 30 Tablets",
                "category": "مزمن - سكر",
                "is_chronic": True,
                "base_price": 35.0,
                "image_url": None,
                "default_cycle_days": 30
            },
            {
                "name": "Cataflam 50mg 20 Tablets",
                "category": "مسكنات",
                "is_chronic": False,
                "base_price": 55.0,
                "image_url": None,
                "default_cycle_days": 10
            }
        ]
        
        print("Re-seeding the 5 test items with NULL images and strict categories...")
        for d in drugs:
            drug_in = DrugCreate(**d)
            db_drug = await create_drug(db, drug_in)
            # Use ASCII safe print
            safe_name = db_drug.name.encode('ascii', 'replace').decode('ascii')
            print(f"Added to DB: {safe_name}")

if __name__ == "__main__":
    asyncio.run(fix_database())
