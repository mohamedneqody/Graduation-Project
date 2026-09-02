import bcrypt
from sqlalchemy import create_engine, text
import uuid
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
password = b"Test1234!"
hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")

email_a = "test_a@example.com"
email_b = "test_b@example.com"

with engine.begin() as conn:
    # 1. Ensure 2 tenants exist
    tenants = conn.execute(text("SELECT tenant_id, name FROM tenants LIMIT 2")).fetchall()
    
    if len(tenants) < 1:
        tid1 = uuid.uuid4()
        conn.execute(text("INSERT INTO tenants (tenant_id, name) VALUES (:id, :n)"), {"id": tid1, "n": "Tenant A"})
    else:
        tid1 = tenants[0].tenant_id

    if len(tenants) < 2:
        tid2 = uuid.uuid4()
        conn.execute(text("INSERT INTO tenants (tenant_id, name) VALUES (:id, :n)"), {"id": tid2, "n": "Tenant B"})
    else:
        tid2 = tenants[1].tenant_id

    # 2. Insert or Update Auth Users
    for email in [email_a, email_b]:
        res = conn.execute(text("SELECT id FROM auth.users WHERE email = :email"), {"email": email}).scalar()
        if not res:
            uid = uuid.uuid4()
            conn.execute(text("""
                INSERT INTO auth.users (id, instance_id, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at, role)
                VALUES (:id, '00000000-0000-0000-0000-000000000000', :email, :pw, now(), '{"provider":"email","providers":["email"]}', '{}', now(), now(), 'authenticated')
            """), {"id": uid, "email": email, "pw": hashed_password})
        else:
            conn.execute(text("UPDATE auth.users SET encrypted_password = :pw WHERE email = :email"), {"pw": hashed_password, "email": email})

    # 3. Ensure customers exist
    uid_a = conn.execute(text("SELECT id FROM auth.users WHERE email = :email"), {"email": email_a}).scalar()
    uid_b = conn.execute(text("SELECT id FROM auth.users WHERE email = :email"), {"email": email_b}).scalar()

    # Customer A
    res_a = conn.execute(text("SELECT customer_id FROM customers WHERE auth_user_id = :uid"), {"uid": uid_a}).scalar()
    if not res_a:
        conn.execute(text("""
            INSERT INTO customers (customer_id, auth_user_id, tenant_id, email, full_name, role)
            VALUES (:cid, :uid, :tid, :email, 'Test User A', 'admin')
        """), {"cid": uuid.uuid4(), "uid": uid_a, "tid": tid1, "email": email_a})
    else:
        conn.execute(text("UPDATE customers SET tenant_id = :tid, role='admin' WHERE auth_user_id = :uid"), {"tid": tid1, "uid": uid_a})

    # Customer B
    res_b = conn.execute(text("SELECT customer_id FROM customers WHERE auth_user_id = :uid"), {"uid": uid_b}).scalar()
    if not res_b:
        conn.execute(text("""
            INSERT INTO customers (customer_id, auth_user_id, tenant_id, email, full_name, role)
            VALUES (:cid, :uid, :tid, :email, 'Test User B', 'admin')
        """), {"cid": uuid.uuid4(), "uid": uid_b, "tid": tid2, "email": email_b})
    else:
        conn.execute(text("UPDATE customers SET tenant_id = :tid, role='admin' WHERE auth_user_id = :uid"), {"tid": tid2, "uid": uid_b})

    print("Success! Test users provisioned.")
    print(f"Tenant A User -> Email: {email_a} | Password: Test1234!")
    print(f"Tenant B User -> Email: {email_b} | Password: Test1234!")
