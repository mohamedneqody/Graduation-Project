import asyncio
import asyncpg

DB_URL = "postgresql://postgres.quhfheudhewxqmvxwjij:010704613318686@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

async def check():
    conn = await asyncpg.connect(DB_URL)
    
    key_tables = ['customers', 'orders', 'order_items', 'drugs', 'tenants']
    
    for tbl in key_tables:
        print(f"\n=== COLUMNS OF {tbl.upper()} ===")
        cols = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=$1 ORDER BY ordinal_position",
            tbl
        )
        for c in cols:
            print(f"  {c['column_name']} ({c['data_type']})")
        
        # Sample rows
        if cols:
            col_names = ', '.join([f'"{c["column_name"]}"' for c in cols[:6]])
            try:
                rows = await conn.fetch(f'SELECT {col_names} FROM {tbl} LIMIT 3')
                print(f"  --- SAMPLE ROWS ---")
                for r in rows:
                    print(f"  {dict(r)}")
            except Exception as e:
                print(f"  Sample error: {e}")
    
    await conn.close()

asyncio.run(check())
