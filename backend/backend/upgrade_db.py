import asyncio
import sys
import os
sys.path.append(os.path.abspath('.'))
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.core.config import settings

async def upgrade_db():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with AsyncSession(engine) as session:
        print("Adding shipping_name...")
        await session.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_name VARCHAR(255);"))
        print("Adding shipping_phone...")
        await session.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_phone VARCHAR(50);"))
        print("Adding shipping_address...")
        await session.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address TEXT;"))
        print("Adding payment_method...")
        await session.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) DEFAULT 'credit_card';"))
        await session.commit()
        print("Database upgraded successfully.")

asyncio.run(upgrade_db())
