import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://aicos_app.quhfheudhewxqmvxwjij:secure_aicos_app_pass_2026@aws-0-eu-central-1.pooler.supabase.com:5432/postgres')
    
    tenant_id = '62712616-be1e-4129-986f-4131877e63b8'
    try:
        await conn.execute(f"""
            INSERT INTO tenants (tenant_id, name, subdomain, is_active, created_at) 
            VALUES ('{tenant_id}', 'PharmaCOS AI (Default)', 'localhost', true, NOW())
            ON CONFLICT (tenant_id) DO NOTHING;
        """)
        print('Tenant inserted successfully')
    except Exception as e:
        print('Error inserting tenant:', e)
        
    await conn.close()

asyncio.run(run())
