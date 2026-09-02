import asyncio
import asyncpg

DB_URL = "postgresql://postgres.quhfheudhewxqmvxwjij:010704613318686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

async def check_role():
    conn = await asyncpg.connect(DB_URL)
    
    # Check if role column exists in customers
    cols = await conn.fetch("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='customers'
    """)
    col_names = [c['column_name'] for c in cols]
    print("Customer columns:", col_names)
    print("Has role column:", 'role' in col_names)
    
    # Check who the admin user is
    if 'role' in col_names:
        rows = await conn.fetch("SELECT customer_id, email, full_name, role FROM customers WHERE role IS NOT NULL LIMIT 5")
        print("\nUsers with roles:")
        for r in rows:
            print(f"  {r['email']} -> role={r['role']}")
    
    # Check SUPER_ADMIN_EMAIL
    super_admin = 'mohameb.eslam460@gmail.com'
    admin_row = await conn.fetchrow("SELECT customer_id, email, full_name, role FROM customers WHERE email=$1", super_admin)
    if admin_row:
        print(f"\nAdmin user: {dict(admin_row)}")
    else:
        print(f"\nAdmin email '{super_admin}' NOT FOUND in customers table")
    
    # Show all tenants
    tenants = await conn.fetch("SELECT tenant_id, name, subdomain FROM tenants ORDER BY created_at LIMIT 5")
    print("\nFirst 5 tenants:")
    for t in tenants:
        print(f"  {t['tenant_id']} | {t['name']} | {t['subdomain']}")
    
    await conn.close()

asyncio.run(check_role())
