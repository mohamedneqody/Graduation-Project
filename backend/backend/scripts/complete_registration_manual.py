import asyncio
import sys
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select
from app.main import app
from app.database.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.dependencies.auth import verify_supabase_jwt

async def run(access_token):
    print('--- Running Manual Registration ---')
    
    payload = verify_supabase_jwt(access_token)
    auth_user_id = payload.get('sub')
    print(f'Decoded auth_user_id from token: {auth_user_id}')
    
    tenant_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        db.add(Tenant(tenant_id=tenant_id, name='Manual Auth Tenant', subdomain=f'manualauth-{uuid.uuid4().hex[:8]}', is_active=True))
        await db.commit()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        headers = {'Authorization': f'Bearer {access_token}'}
        reg_payload = {'tenant_id': str(tenant_id), 'full_name': 'Manual Supabase User', 'phone': '+20102222222'}
        res = await ac.post('/api/v1/auth/complete-registration', json=reg_payload, headers=headers)
        
        print(f'Complete Registration Response Status: {res.status_code}')
        if res.status_code == 200:
            print('Complete Registration Success!', res.json())
        else:
            print('Complete Registration Failed:', res.text)
            
    async with AsyncSessionLocal() as db:
        customer_res = await db.execute(select(Customer).where(Customer.auth_user_id == auth_user_id))
        customer = customer_res.scalars().first()
        if customer:
            print(f'NEW CUSTOMER FOUND IN DB! ID: {customer.customer_id}, Name: {customer.full_name}, auth_user_id: {customer.auth_user_id}')
        else:
            print('NEW CUSTOMER NOT FOUND in DB!')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python complete_registration_manual.py <access_token>')
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))