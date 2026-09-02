import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import text, select
from app.models.customer import Customer

async def main():
    async with AsyncSessionLocal() as db:
        try:
            # First, find the user by email without RLS (maybe RLS doesn't apply to SELECT if it's disabled, or we just use raw SQL with postgres if possible? No, we are aicos_app)
            # Actually, let's bypass RLS by disabling it for the transaction if possible.
            # aicos_app might not have permission to disable RLS, but let's try.
            # Wait, in Supabase, you can set the role to postgres if you have privileges? Probably not.
            # Let's just try to find the auth_user_id first
            res = await db.execute(text("SELECT auth_user_id, email, role FROM customers WHERE email = 'mohameb.eslam460@gmail.com'"))
            row = res.first()
            if not row:
                print("Could not find user. RLS is probably blocking.")
                # We can bypass RLS in Postgres by creating a security definer function, but we can't do that without superuser.
                # Is there a way to bypass RLS?
                # Let's try to set role to postgres (might fail)
            else:
                print(f"Found! {row}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
