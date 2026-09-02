import asyncio
import uuid
from sqlalchemy import create_engine, text
from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client using Anon Key
supabase: Client = create_client(
    settings.NEXT_PUBLIC_SUPABASE_URL,
    settings.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
)

engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))

email_a = "admin_a@example.com"
email_b = "admin_b@example.com"
password = "Test1234!"

def signup_user(email):
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        if res.user:
            return res.user.id
    except Exception as e:
        print(f"Signup error for {email} (might already exist): {e}")
    # Try login to get ID if already exists
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res.user:
            return res.user.id
    except Exception as e:
        print(f"Login error for {email}: {e}")
    return None

def main():
    print("Signing up users via Supabase API (GoTrue)...")
    uid_a = signup_user(email_a)
    uid_b = signup_user(email_b)

    if not uid_a or not uid_b:
        print("Failed to sign up or log in users. Cannot proceed.")
        return

    print(f"Got UIDs: A={uid_a}, B={uid_b}")

    with engine.begin() as conn:
        # Confirm emails directly in auth.users just in case email confirmations are enabled
        conn.execute(text("UPDATE auth.users SET email_confirmed_at = now() WHERE id IN (:id_a, :id_b)"), {"id_a": uid_a, "id_b": uid_b})
        
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

        # 2. Sync to customers table
        # Customer A
        res_a = conn.execute(text("SELECT customer_id FROM customers WHERE auth_user_id = :uid"), {"uid": uid_a}).scalar()
        if not res_a:
            conn.execute(text("""
                INSERT INTO customers (customer_id, auth_user_id, tenant_id, email, full_name, role)
                VALUES (:cid, :uid, :tid, :email, 'Admin A', 'admin')
            """), {"cid": uuid.uuid4(), "uid": uid_a, "tid": tid1, "email": email_a})
        else:
            conn.execute(text("UPDATE customers SET tenant_id = :tid, role='admin' WHERE auth_user_id = :uid"), {"tid": tid1, "uid": uid_a})

        # Customer B
        res_b = conn.execute(text("SELECT customer_id FROM customers WHERE auth_user_id = :uid"), {"uid": uid_b}).scalar()
        if not res_b:
            conn.execute(text("""
                INSERT INTO customers (customer_id, auth_user_id, tenant_id, email, full_name, role)
                VALUES (:cid, :uid, :tid, :email, 'Admin B', 'admin')
            """), {"cid": uuid.uuid4(), "uid": uid_b, "tid": tid2, "email": email_b})
        else:
            conn.execute(text("UPDATE customers SET tenant_id = :tid, role='admin' WHERE auth_user_id = :uid"), {"tid": tid2, "uid": uid_b})

    print("Success! Users properly registered in Supabase GoTrue and linked to different tenants.")
    print(f"Tenant A User -> Email: {email_a} | Password: {password}")
    print(f"Tenant B User -> Email: {email_b} | Password: {password}")

if __name__ == "__main__":
    main()
