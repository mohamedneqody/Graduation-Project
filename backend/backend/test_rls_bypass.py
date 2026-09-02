import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine(os.environ.get("DATABASE_URL"))
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT count(*) FROM customers"))
        print(f"Total customers: {result.scalar()}")
        
        # Check current role and bypassrls status
        role_info = await conn.execute(text("SELECT current_user, (SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user)"))
        role, bypass = role_info.fetchone()
        print(f"Role: {role}, Bypasses RLS: {bypass}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test())
