import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_drug_domain():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        print("1. Creating Drug 1...")
        res1 = await client.post("/api/v1/drugs/", json={
            "name": "Aspirin",
            "category": "Painkiller",
            "is_chronic": False,
            "base_price": 10.5,
            "default_cycle_days": 10
        })
        print(res1.status_code, res1.json())
        drug1_id = res1.json().get("drug_id")
        
        print("\n2. Creating Drug 2...")
        res2 = await client.post("/api/v1/drugs/", json={
            "name": "Ibuprofen",
            "category": "Painkiller",
            "is_chronic": False,
            "base_price": 15.0,
            "default_cycle_days": 14
        })
        print(res2.status_code, res2.json())
        drug2_id = res2.json().get("drug_id")
        
        print("\n3. Testing check-interactions (should be empty)...")
        res_check1 = await client.post("/api/v1/drugs/check-interactions", json={"drug_ids": [drug1_id, drug2_id]})
        print(res_check1.status_code, res_check1.json())
        
        print("\n4. Creating interaction between Drug 1 and Drug 2...")
        res_interaction = await client.post("/api/v1/drugs/interactions", json={
            "drug_id_a": drug1_id,
            "drug_id_b": drug2_id,
            "severity": "high",
            "note": "Increased risk of bleeding"
        })
        print(res_interaction.status_code, res_interaction.json())
        
        print("\n5. Testing check-interactions again (should find the interaction)...")
        res_check2 = await client.post("/api/v1/drugs/check-interactions", json={"drug_ids": [drug1_id, drug2_id]})
        print(res_check2.status_code, res_check2.json())
        
        print("\n6. Testing pagination, filtering, sorting...")
        res_list = await client.get("/api/v1/drugs/?page=1&limit=10&category=Painkiller&sort_by=base_price&sort_order=desc")
        print(res_list.status_code, res_list.json())

if __name__ == "__main__":
    asyncio.run(test_drug_domain())
