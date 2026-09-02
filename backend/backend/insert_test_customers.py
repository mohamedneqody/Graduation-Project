from sqlalchemy import create_engine, text
from app.core.config import settings
import uuid

engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))

with engine.begin() as conn:
    # Get tenants
    tenants = conn.execute(text("SELECT tenant_id FROM tenants LIMIT 2")).fetchall()
    tid_a = tenants[0].tenant_id
    tid_b = tenants[1].tenant_id
    
    # Insert dummy customers for visualization
    cid_a = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO customers (customer_id, auth_user_id, tenant_id, email, full_name, role)
        VALUES (:cid, :uid, :tid, :email, 'REALTIME UPDATE - TENANT A', 'customer')
    """), {"cid": cid_a, "uid": uuid.uuid4(), "tid": tid_a, "email": "test_dummy_a@example.com"})

    cid_b = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO customers (customer_id, auth_user_id, tenant_id, email, full_name, role)
        VALUES (:cid, :uid, :tid, :email, 'REALTIME UPDATE - TENANT B', 'customer')
    """), {"cid": cid_b, "uid": uuid.uuid4(), "tid": tid_b, "email": "test_dummy_b@example.com"})

print("Inserted test customers for Tenant A and Tenant B.")
