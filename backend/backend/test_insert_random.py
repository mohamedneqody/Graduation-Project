import asyncio
import asyncpg
import os
import uuid
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    try:
        await conn.execute("""
            INSERT INTO customers (customer_id, auth_user_id, tenant_id, email, full_name, phone, preferred_channel, preferred_language, role, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, 
        uuid.uuid4(), uuid.uuid4(), uuid.UUID('62712616-be1e-4129-986f-4131877e63b8'),
        'test999999@gmail.com', 'Test User', '010704613313', 'email', 'ar', 'customer', True)
        print("Insert successful!")
    except Exception as e:
        print("Insert failed with error:", type(e))
        print(e)
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
