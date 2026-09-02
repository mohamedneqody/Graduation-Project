import asyncio
import os
import sys

# Append the project root to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def apply_fixes():
    # We must connect using the current postgres user which has superuser/bypassrls privileges
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("Creating role aicos_app...")
        # Check if role exists
        res = await conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname='aicos_app'"))
        if not res.scalar():
            await conn.execute(text("CREATE ROLE aicos_app LOGIN PASSWORD 'secure_aicos_app_pass_2026'"))
            print("Role aicos_app created.")
        else:
            print("Role aicos_app already exists.")
            # optionally change password
            await conn.execute(text("ALTER ROLE aicos_app WITH PASSWORD 'secure_aicos_app_pass_2026'"))
            
        print("Granting permissions to aicos_app...")
        await conn.execute(text("GRANT USAGE ON SCHEMA public TO aicos_app"))
        await conn.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aicos_app"))
        await conn.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aicos_app"))
        await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO aicos_app"))
        await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO aicos_app"))
        
        # Ensure it does NOT have BYPASSRLS
        await conn.execute(text("ALTER ROLE aicos_app NOBYPASSRLS"))
        
        print("Enabling RLS on tenant_settings...")
        await conn.execute(text("ALTER TABLE IF EXISTS tenant_settings ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text("ALTER TABLE IF EXISTS tenant_settings FORCE ROW LEVEL SECURITY"))
        
        print("Creating RLS Policy for tenant_settings...")
        # Drop if exists
        try:
            await conn.execute(text("DROP POLICY IF EXISTS tenant_settings_isolation ON tenant_settings"))
        except Exception:
            pass
            
        # Create policy
        policy_sql = """
        CREATE POLICY tenant_settings_isolation ON tenant_settings
            FOR ALL
            USING (
                tenant_id = current_user_tenant_id() OR current_user_tenant_id() IS NULL
            )
            WITH CHECK (
                tenant_id = current_user_tenant_id() OR current_user_tenant_id() IS NULL
            );
        """
        await conn.execute(text(policy_sql))
        print("Policy created.")

    await engine.dispose()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(apply_fixes())
