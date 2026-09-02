import asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.tenant import Tenant
import json

async def test_notification_loop():
    print("Getting a tenant and due customers...")
    
    tenant_id = None
    target_customer_id = None
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        tenant = (await db.execute(select(Tenant).limit(1))).scalars().first()
        tenant_id = tenant.tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Check due reminders (Before sending notification)
        print("\n--- STEP 1: Fetching Due Reminders ---")
        response1 = await client.get(f"/internal/cycles/due-reminders?tenant_id={tenant_id}")
        data1 = response1.json()
        
        # Look for customer '9038882c-cebe-40c9-832d-1eee1adf9552' (whatsapp customer with 2 drugs from previous test)
        # or just take the first customer
        if not data1:
            print("No due reminders found. Please run test_fallback_contacts.py first to seed data.")
            return
            
        target_customer = data1[0]
        target_customer_id = target_customer["customer_id"]
        print(f"Customer {target_customer_id} is DUE for a reminder.")
        print("Drugs due:", [d["drug_name"] for d in target_customer["due_drugs"]])
        
        # 2. Simulate n8n sending message and calling POST /record
        print("\n--- STEP 2: Recording Sent Notification (n8n simulation) ---")
        payload = {
            "customer_id": target_customer_id,
            "notification_type": "reminder",
            "channel": target_customer["preferred_channel"],
            "status": "sent"
        }
        response2 = await client.post("/internal/notifications/record", json=payload)
        print(f"Record API Status: {response2.status_code}")
        print(f"Record API Response: {response2.json()}")
        
        # 3. Check due reminders again (After sending notification)
        print("\n--- STEP 3: Fetching Due Reminders AGAIN ---")
        response3 = await client.get(f"/internal/cycles/due-reminders?tenant_id={tenant_id}")
        data3 = response3.json()
        
        found = any(c["customer_id"] == target_customer_id for c in data3)
        if found:
            print(f"❌ FAIL: Customer {target_customer_id} is STILL in the due reminders list!")
        else:
            print(f"✅ SUCCESS: Customer {target_customer_id} has been FILTERED OUT of the list because a notification was sent in the last 24h.")
            
if __name__ == "__main__":
    asyncio.run(test_notification_loop())
