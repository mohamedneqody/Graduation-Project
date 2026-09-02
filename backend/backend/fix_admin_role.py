import asyncio
import asyncpg

DB_URL = "postgresql://postgres.quhfheudhewxqmvxwjij:010704613318686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
ADMIN_EMAIL = "mohameb.eslam460@gmail.com"
MAIN_TENANT = "62712616-be1e-4129-986f-4131877e63b8"

async def go():
    conn = await asyncpg.connect(DB_URL)
    
    # 1. Check columns
    cols = await conn.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='customers' ORDER BY ordinal_position"
    )
    names = [c['column_name'] for c in cols]
    print("COLUMNS:", names)
    has_role = 'role' in names
    print("HAS role column:", has_role)
    
    # 2. Check admin user
    if has_role:
        r = await conn.fetchrow(
            "SELECT customer_id, email, role FROM customers WHERE email=$1", ADMIN_EMAIL
        )
        print("ADMIN ROW:", dict(r) if r else "NOT FOUND")
        
        # Set admin role
        if r and r['role'] != 'admin':
            await conn.execute(
                "UPDATE customers SET role='admin' WHERE email=$1", ADMIN_EMAIL
            )
            print(">>> Set role=admin for", ADMIN_EMAIL)
        elif r and r['role'] == 'admin':
            print("Already admin!")
    else:
        # No role column - need to add it
        print("Need to ADD role column to customers table")
        await conn.execute(
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'customer'"
        )
        await conn.execute(
            "UPDATE customers SET role='admin' WHERE email=$1", ADMIN_EMAIL
        )
        print(">>> Added role column and set admin for", ADMIN_EMAIL)
    
    # 3. Verify
    r2 = await conn.fetchrow(
        "SELECT customer_id, email, role FROM customers WHERE email=$1", ADMIN_EMAIL
    )
    print("FINAL ADMIN:", dict(r2) if r2 else "STILL NOT FOUND")
    
    # 4. Count drugs in main tenant
    drug_count = await conn.fetchval("SELECT COUNT(*) FROM drugs")
    print(f"\nTotal drugs: {drug_count}")
    
    # Sample drugs
    drugs = await conn.fetch("SELECT name, category, base_price, image_url FROM drugs LIMIT 5")
    print("Sample drugs:")
    for d in drugs:
        print(f"  {d['name']} | {d['category']} | {d['base_price']} | img={d['image_url'][:50] if d['image_url'] else 'NULL'}")
    
    await conn.close()

asyncio.run(go())
