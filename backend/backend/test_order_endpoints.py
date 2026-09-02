import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.dependencies.auth import get_current_user
import uuid

async def setup_data():
    async with AsyncSessionLocal() as db:
        # Get or create tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalars().first()
        if not tenant:
            tenant = Tenant(name="Test Pharmacy", domain="test.ai-cos.com")
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            
        # Get or create customer 1
        result = await db.execute(select(Customer).limit(2))
        customers = result.scalars().all()
        
        if len(customers) < 2:
            # Create two customers
            c1 = Customer(tenant_id=tenant.tenant_id, email="c1@test.com", auth_user_id=str(uuid.uuid4()))
            c2 = Customer(tenant_id=tenant.tenant_id, email="c2@test.com", auth_user_id=str(uuid.uuid4()))
            db.add_all([c1, c2])
            await db.commit()
            await db.refresh(c1)
            await db.refresh(c2)
            customer1 = c1
            customer2 = c2
        else:
            customer1 = customers[0]
            customer2 = customers[1]
            
    return customer1, customer2

async def test_order_domain():
    c1, c2 = await setup_data()
    print(f"Using Customer 1: {c1.customer_id}")
    print(f"Using Customer 2: {c2.customer_id}")
    
    # Override auth to Customer 1
    app.dependency_overrides[get_current_user] = lambda: c1
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Create two drugs
        d1_res = await client.post("/api/v1/drugs/", json={"name": "Drug A", "category": "Test", "base_price": 50.0})
        d2_res = await client.post("/api/v1/drugs/", json={"name": "Drug B", "category": "Test", "base_price": 20.0})
        drug_a_id = d1_res.json()["drug_id"]
        drug_b_id = d2_res.json()["drug_id"]
        print("Created drugs:", drug_a_id, drug_b_id)
        
        # 2. Add HIGH interaction
        await client.post("/api/v1/drugs/interactions", json={
            "drug_id_a": drug_a_id,
            "drug_id_b": drug_b_id,
            "severity": "high",
            "note": "Fatal interaction"
        })
        
        # 3. Test Order Creation with HIGH interaction -> Should be 422
        print("\nTesting Order with HIGH interaction (Expect 422)...")
        order_res_fail = await client.post("/api/v1/orders/", json={
            "items": [{"drug_id": drug_a_id, "quantity": 1}, {"drug_id": drug_b_id, "quantity": 2}],
            "channel": "web"
        })
        print("Status:", order_res_fail.status_code)
        print("Response:", order_res_fail.json())
        assert order_res_fail.status_code == 422
        
        # 4. Create two SAFE drugs
        d3_res = await client.post("/api/v1/drugs/", json={"name": "Drug C", "category": "Test", "base_price": 10.0})
        d4_res = await client.post("/api/v1/drugs/", json={"name": "Drug D", "category": "Test", "base_price": 30.0})
        drug_c_id = d3_res.json()["drug_id"]
        drug_d_id = d4_res.json()["drug_id"]
        
        # 5. Test Successful Order
        print("\nTesting Order with SAFE drugs (Expect 201)...")
        order_res_ok = await client.post("/api/v1/orders/", json={
            "items": [{"drug_id": drug_c_id, "quantity": 2}, {"drug_id": drug_d_id, "quantity": 1}],
            "channel": "app"
        })
        print("Status:", order_res_ok.status_code)
        print("Response:", order_res_ok.json())
        assert order_res_ok.status_code == 201
        
        order_id = order_res_ok.json()["order_id"]
        total = order_res_ok.json()["total_amount"]
        # Drug C: 2 * 10 = 20
        # Drug D: 1 * 30 = 30
        # Total should be 50.0
        print("Total amount calculated:", total)
        assert total == 50.0
        
        # 6. Test isolated access
        print("\nTesting GET Order as Customer 1 (Expect 200)...")
        get_res_c1 = await client.get(f"/api/v1/orders/{order_id}")
        print("Status:", get_res_c1.status_code)
        assert get_res_c1.status_code == 200
        
        # Override to Customer 2
        app.dependency_overrides[get_current_user] = lambda: c2
        print("\nTesting GET Order as Customer 2 (Expect 404)...")
        get_res_c2 = await client.get(f"/api/v1/orders/{order_id}")
        print("Status:", get_res_c2.status_code)
        print("Response:", get_res_c2.json())
        assert get_res_c2.status_code == 404
        
if __name__ == "__main__":
    asyncio.run(test_order_domain())
