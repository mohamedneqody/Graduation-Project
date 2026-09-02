import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from httpx import ASGITransport, AsyncClient

# Setup path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from app.dependencies.auth import verify_supabase_jwt, get_db
from app.domains.auth.router import RegistrationRequest
from app.models.customer import Customer
import uuid

# Create a fake UUID for our mock user
FAKE_AUTH_USER_ID = str(uuid.uuid4())
FAKE_EMAIL = "test_oauth@example.com"

async def mock_verify_supabase_jwt(token: str) -> dict:
    # Simulate Supabase successfully verifying a Google/Facebook/GitHub token
    print(f"[Mock] Verifying token: {token}")
    return {
        "sub": FAKE_AUTH_USER_ID,
        "email": FAKE_EMAIL
    }

# Override the dependency
app.dependency_overrides[verify_supabase_jwt] = mock_verify_supabase_jwt

async def run_test():
    print("--- Testing complete-registration Logic ---")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Mock payload from Frontend
        payload = {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "full_name": "Test User",
            "phone": "+1234567890",
            "age_group": "adult",
            "preferred_channel": "whatsapp",
            "preferred_language": "ar"
        }
        
        # Send POST request simulating a logged-in user passing their JWT
        headers = {"Authorization": "Bearer fake_google_or_facebook_token"}
        print(f"Sending POST /api/v1/auth/complete-registration with payload: {payload}")
        
        response = await client.post(
            "/api/v1/auth/complete-registration",
            json=payload,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            print("✅ SUCCESS: The backend successfully registered the user from the OAuth/Manual token!")
            
            # Verify in DB
            print("Verifying in Database...")
            from app.database.session import SessionLocal
            async with SessionLocal() as db:
                result = await db.execute(select(Customer).where(Customer.auth_user_id == FAKE_AUTH_USER_ID))
                customer = result.scalars().first()
                if customer:
                    print(f"✅ FOUND IN DB: {customer.full_name} | {customer.email} | {customer.age_group}")
                else:
                    print("❌ ERROR: Not found in DB.")
        elif response.status_code == 400 and "already completed" in str(response.json()):
            print("✅ SUCCESS (Idempotent): User already exists.")
        else:
            print("❌ ERROR: Unexpected status code.")

if __name__ == "__main__":
    # Ensure env is loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(run_test())
