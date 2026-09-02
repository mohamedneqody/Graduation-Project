import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
import os
from dotenv import load_dotenv

async def main():
    load_dotenv('D:/Graduation Project/backend/backend/.env', override=True)
    engine = create_async_engine(os.environ.get('DATABASE_URL'))
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    from app.models.customer import Customer
    from app.domains.customer import schemas
    
    import uuid
    
    async with SessionLocal() as db:
        customer_in = schemas.CustomerCreate(
            email="test7777777777@gmail.com",
            full_name="Test",
            phone="010704613313",
        )
        customer_in.tenant_id = uuid.UUID('62712616-be1e-4129-986f-4131877e63b8')
        
        try:
            db_customer = Customer(
                auth_user_id=customer_in.auth_user_id or uuid.uuid4(),
                tenant_id=customer_in.tenant_id,
                email=customer_in.email,
                full_name=customer_in.full_name,
                phone=customer_in.phone,
                age_group=customer_in.age_group,
                preferred_channel=customer_in.preferred_channel,
                preferred_language=customer_in.preferred_language
            )
            db.add(db_customer)
            await db.commit()
            print("Successfully inserted test7777777777@gmail.com via SQLAlchemy!")
        except Exception as e:
            print("Failed:", type(e))
            print(e)
            
if __name__ == '__main__':
    asyncio.run(main())
