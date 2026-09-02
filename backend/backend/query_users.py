import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))

with engine.connect() as conn:
    print("--- Users ---")
    users = conn.execute(text("SELECT id, email, confirmed_at FROM auth.users")).fetchall()
    for u in users:
        print(f"ID: {u.id}, Email: {u.email}, Confirmed: {u.confirmed_at}")

    print("--- Tenants ---")
    tenants = conn.execute(text("SELECT tenant_id, name FROM tenants")).fetchall()
    for t in tenants:
        print(f"ID: {t.tenant_id}, Name: {t.name}")

    print("--- Customers ---")
    customers = conn.execute(text("SELECT customer_id, email, tenant_id FROM customers")).fetchall()
    for c in customers:
        print(f"ID: {c.customer_id}, Email: {c.email}, Tenant: {c.tenant_id}")
