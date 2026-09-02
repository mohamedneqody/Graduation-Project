import os
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

async def main():
    load_dotenv()
    engine = create_async_engine(os.environ.get('DATABASE_URL'))
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT email, auth_user_id, customer_id, tenant_id FROM customers WHERE email IN ('tenant_a@test.com', 'tenant_b@test.com')"))
        rows = res.fetchall()
        for r in rows:
            print(f'{r.email} | auth: {r.auth_user_id} | customer: {r.customer_id} | tenant: {r.tenant_id}')
            
        if len(rows) == 0:
            print("No users found. I need to insert them.")
            t_a = str(uuid.uuid4())
            t_b = str(uuid.uuid4())
            await conn.execute(text(f"INSERT INTO tenants (tenant_id, name, subdomain, is_active) VALUES ('{t_a}', 'Live Tenant A', 'live-a', true)"))
            await conn.execute(text(f"INSERT INTO tenants (tenant_id, name, subdomain, is_active) VALUES ('{t_b}', 'Live Tenant B', 'live-b', true)"))
            c_a = str(uuid.uuid4())
            c_b = str(uuid.uuid4())
            await conn.execute(text(f"INSERT INTO customers (customer_id, tenant_id, auth_user_id, email, full_name, phone, is_active) VALUES ('{c_a}', '{t_a}', '5b63d95c-24d0-4599-9d5d-2232252096b1', 'tenant_a@test.com', 'Live User A', '+201000000001', true)"))
            await conn.execute(text(f"INSERT INTO customers (customer_id, tenant_id, auth_user_id, email, full_name, phone, is_active) VALUES ('{c_b}', '{t_b}', '71fb0a51-e57c-4716-b6cd-6c3ae1743f26', 'tenant_b@test.com', 'Live User B', '+201000000002', true)"))
            print("Inserted A and B")
        
        # Insert target customer with dummy auth_user_id to satisfy NOT NULL
        # Get t_a from the first row or newly created
        res = await conn.execute(text("SELECT tenant_id FROM customers WHERE email = 'tenant_a@test.com'"))
        row = res.fetchone()
        if row:
            t_a = row[0]
            target_c_a = str(uuid.uuid4())
            dummy_auth = str(uuid.uuid4())
            await conn.execute(text(f"INSERT INTO customers (customer_id, tenant_id, auth_user_id, email, full_name, phone, is_active) VALUES ('{target_c_a}', '{t_a}', '{dummy_auth}', 'target_a_{target_c_a[:8]}@test.com', 'Target A', '+201000000003', true)"))
            print(f'Target A Customer ID: {target_c_a}')

if __name__ == '__main__':
    asyncio.run(main())
