import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
TENANT_ID = "62712616-be1e-4129-986f-4131877e63b8"
HEADERS = {"X-N8N-Service-Key": "dev-secret-key-12345-very-long-and-secure-32-chars"}

async def seed_via_api():
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Get due reminders
        print("Fetching due reminders (this might take a while because it runs ML predictions)...")
        resp = await client.get(f"{BASE_URL}/internal/cycles/due-reminders?tenant_id={TENANT_ID}", headers=HEADERS)
        if resp.status_code != 200:
            print("Failed to fetch due reminders:", resp.text)
            return
            
        customers = resp.json()
        if not customers:
            print("No customers found in due-reminders!")
            return
            
        print(f"Found {len(customers)} customers.")
        
        # 2. Evaluate the first one
        target_customer = customers[0]
        c_id = target_customer["customer_id"]
        d_id = target_customer["due_drugs"][0]["drug_id"]
        
        payload = {
            "customer_id": c_id,
            "drug_id": d_id,
            "channel": "whatsapp"
        }
        
        print(f"Evaluating governance for customer {c_id} and drug {d_id}...")
        eval_resp = await client.post(f"{BASE_URL}/internal/governance/evaluate", json=payload, headers=HEADERS)
        
        if eval_resp.status_code == 200:
            print("✅ Successfully evaluated and inserted into pending_reminders!")
            print(json.dumps(eval_resp.json(), indent=2))
        else:
            print("Failed to evaluate:", eval_resp.text)

if __name__ == "__main__":
    asyncio.run(seed_via_api())
