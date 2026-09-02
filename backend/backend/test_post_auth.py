import asyncio
import httpx
import os
import jwt
import time
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    key = os.environ.get('SUPABASE_JWT_SECRET')
    
    # In 'customers', the user 'mohameb.eslam460@gmail.com' is an admin.
    # What is their auth_user_id? 
    # Let's check from the DB using asyncpg first.
    import asyncpg
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    res = await conn.fetchrow("SELECT auth_user_id, tenant_id FROM customers WHERE email = 'mohameb.eslam460@gmail.com'")
    if not res:
        print("Admin user not found!")
        await conn.close()
        return
        
    admin_auth_user_id = str(res['auth_user_id'])
    tenant_id = str(res['tenant_id'])
    await conn.close()

    # Generate a JWT that looks like a Supabase authenticated token
    # The 'sub' claim should be the auth_user_id.
    token = jwt.encode({
        'role': 'authenticated',
        'sub': admin_auth_user_id,
        'email': 'mohameb.eslam460@gmail.com',
        'exp': int(time.time()) + 3600
    }, key, algorithm='HS256')

    headers = {
        'Authorization': f'Bearer {token}',
        'X-Tenant-ID': tenant_id,
        'Content-Type': 'application/json'
    }

    # Test POST
    payload = {
        "full_name": "Test Customer",
        "email": "test888888@gmail.com",
        "phone": "010704613313"
    }
    
    async with httpx.AsyncClient() as client:
        res2 = await client.post('http://127.0.0.1:8000/api/v1/customers/', json=payload, headers=headers)
        print("Status:", res2.status_code)
        print("Response:", res2.text)

if __name__ == '__main__':
    asyncio.run(main())
