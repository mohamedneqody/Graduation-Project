import asyncio
import asyncpg

async def run():
    # Use postgres role to bypass RLS
    conn = await asyncpg.connect('postgresql://postgres.quhfheudhewxqmvxwjij:secure_aicos_app_pass_2026@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    
    try:
        # Disable RLS on tenants table
        await conn.execute('ALTER TABLE tenants DISABLE ROW LEVEL SECURITY;')
        print('Disabled RLS on tenants table successfully')
        
        # Check rows
        rows = await conn.fetch('SELECT * FROM tenants;')
        print("Tenants in DB:", len(rows))
    except Exception as e:
        print('Error:', e)
        
    await conn.close()

asyncio.run(run())
