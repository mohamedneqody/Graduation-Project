"""enable_rls_customers

Revision ID: a165179f481d
Revises: 0003_ab_tests
Create Date: 2026-08-10 01:44:16.122812
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a165179f481d'
down_revision: Union[str, None] = '0003_ab_tests'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the tenant resolution function
    op.execute("""
    CREATE OR REPLACE FUNCTION public.current_user_tenant_id()
    RETURNS uuid
    LANGUAGE sql
    SECURITY DEFINER
    SET search_path = public
    STABLE
    AS $$
        SELECT tenant_id 
        FROM public.customers 
        WHERE auth_user_id = auth.uid() 
        LIMIT 1;
    $$;
    """)

    # 2. Enable RLS on customers
    op.execute("ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;")

    # 3. Create Policy for customers
    op.execute("DROP POLICY IF EXISTS tenant_isolation_customers ON public.customers;")
    op.execute("""
    CREATE POLICY tenant_isolation_customers ON public.customers
    FOR ALL
    USING (
        tenant_id = public.current_user_tenant_id()
    )
    WITH CHECK (
        tenant_id = public.current_user_tenant_id()
    );
    """)

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_customers ON public.customers;")
    op.execute("ALTER TABLE public.customers DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP FUNCTION IF EXISTS public.current_user_tenant_id();")
