import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    url = os.environ.get('DATABASE_URL').replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    try:
        # Drop the unique index on email
        await conn.execute("DROP INDEX IF EXISTS ix_customers_email;")
        # Create a regular index for fast lookups
        await conn.execute("CREATE INDEX ix_customers_email ON customers (email);")
        # Ensure email is only unique per tenant (optional, but better)
        await conn.execute("ALTER TABLE customers ADD CONSTRAINT unique_email_per_tenant UNIQUE (tenant_id, email);")
        print("Database schema successfully fixed! Duplicate emails across the system are now allowed, but unique per pharmacy.")
    except Exception as e:
        print("Error fixing DB:", e)
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
