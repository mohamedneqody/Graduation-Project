from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))

with engine.connect() as conn:
    print("--- Customers ---")
    customers = conn.execute(text("SELECT customer_id, email, auth_user_id FROM customers")).fetchall()
    for c in customers:
        if c.email in ("admin_a@example.com", "admin_b@example.com"):
            print(f"Email: {c.email}, Auth_ID: {c.auth_user_id}")
