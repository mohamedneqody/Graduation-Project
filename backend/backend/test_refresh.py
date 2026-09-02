import asyncio
import os
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    engine = create_async_engine(os.environ.get('DATABASE_URL'))
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    from app.models.customer import Customer
    
    async with SessionLocal() as db:
        db_customer = Customer(
            auth_user_id=uuid.uuid4(), 
            tenant_id=uuid.UUID('62712616-be1e-4129-986f-4131877e63b8'), 
            email='retryingtest_refresh@gmail.com'
        )
        db.add(db_customer)
        await db.commit()
        try:
            await db.refresh(db_customer)
            print('Refresh succeeded')
        except Exception as e:
            print('Refresh failed:', type(e), e)
            
if __name__ == '__main__':
    asyncio.run(main())
