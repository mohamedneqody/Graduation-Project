import asyncio
import uuid
from datetime import date
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, insert, delete
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.tracking import CustomerCycle, Notification

async def test_due_reminders():
    print("Setting up test data...")
    async with AsyncSessionLocal() as db:
        # Get tenant
        tenant = (await db.execute(select(Tenant).limit(1))).scalars().first()
        if not tenant:
            print("No tenant found!")
            return

        # Clean old test customers
        await db.execute(delete(CustomerCycle).where(
            CustomerCycle.customer_id.in_(
                select(Customer.customer_id).where(Customer.email.in_(["email_pref@test.com", "whatsapp_pref@test.com", "wa_fallback@test.com"]))
            )
        ))
        await db.execute(delete(Customer).where(Customer.email.in_(["email_pref@test.com", "whatsapp_pref@test.com", "wa_fallback@test.com"])))
        
        # Get 2 drugs
        drugs = (await db.execute(select(Drug).limit(2))).scalars().all()
        drug1, drug2 = drugs[0], drugs[1]

        # 1. Customer with email preference
        cust1 = Customer(
            auth_user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="email_pref@test.com",
            phone="+2011111111",
            preferred_channel="email"
        )
        db.add(cust1)
        
        # 2. Customer with whatsapp preference (has phone)
        cust2 = Customer(
            auth_user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="whatsapp_pref@test.com",
            phone="+2012222222",
            preferred_channel="whatsapp"
        )
        db.add(cust2)
        
        # 3. Customer with whatsapp preference (no phone - fallback)
        cust3 = Customer(
            auth_user_id=uuid.uuid4(),
            tenant_id=tenant.tenant_id,
            email="wa_fallback@test.com",
            phone=None,
            preferred_channel="whatsapp"
        )
        db.add(cust3)

        await db.commit()
        await db.refresh(cust1)
        await db.refresh(cust2)
        await db.refresh(cust3)

        today = date.today()

        # Add customer cycles for cust1 (1 drug)
        db.add(CustomerCycle(
            customer_id=cust1.customer_id,
            drug_id=drug1.drug_id,
            avg_cycle_days=30,
            last_purchase_date=today,
            reminder_day=today
        ))

        # Add customer cycles for cust2 (2 drugs)
        db.add(CustomerCycle(
            customer_id=cust2.customer_id,
            drug_id=drug1.drug_id,
            avg_cycle_days=15,
            last_purchase_date=today,
            reminder_day=today
        ))
        db.add(CustomerCycle(
            customer_id=cust2.customer_id,
            drug_id=drug2.drug_id,
            avg_cycle_days=20,
            last_purchase_date=today,
            reminder_day=today
        ))
        
        # Add customer cycles for cust3 (1 drug)
        db.add(CustomerCycle(
            customer_id=cust3.customer_id,
            drug_id=drug1.drug_id,
            avg_cycle_days=40,
            last_purchase_date=today,
            reminder_day=today
        ))

        await db.commit()

        print("Testing API...")
        # Since this is an internal n8n endpoint, we just pass tenant_id
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get(f"/internal/cycles/due-reminders?tenant_id={tenant.tenant_id}")
            print(f"Status: {response.status_code}")
            
            import json
            data = response.json()
            
            # Filter output for just our test customers for clarity
            test_emails = ["email_pref@test.com", "whatsapp_pref@test.com", "wa_fallback@test.com"]
            test_contacts = ["email_pref@test.com", "+2012222222", "wa_fallback@test.com"]
            
            filtered = [item for item in data if item.get("customer_contact") in test_contacts]
            print(json.dumps(filtered, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_due_reminders())
