"""apply_rls_all_tables

Revision ID: c89fa4cf264b
Revises: 6da1c746fdff
Create Date: 2026-08-10 13:32:38.256086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c89fa4cf264b'
down_revision: Union[str, None] = '6da1c746fdff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables with tenant_id -> tenant_isolation
    tenanted_tables = [
        "ab_tests",
        "sessions",
        "tenants",
        "notifications",
        "audit_logs",
        "knowledge_chunks"
    ]
    
    for table in tenanted_tables:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON public.{table};")
        op.execute(f"""
        CREATE POLICY tenant_isolation_{table} ON public.{table}
        FOR ALL
        USING (
            tenant_id = public.current_user_tenant_id()
        )
        WITH CHECK (
            tenant_id = public.current_user_tenant_id()
        );
        """)

    # Tables without tenant_id -> global_read
    untenanted_tables = [
        "drug_interactions",
        "drug_affinities",
        "customer_cycles",
        "events",
        "pending_reminders",
        "ab_test_results"
    ]
    
    for table in untenanted_tables:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS global_read_{table} ON public.{table};")
        op.execute(f"""
        CREATE POLICY global_read_{table} ON public.{table}
        FOR SELECT
        USING (true);
        """)


def downgrade() -> None:
    tenanted_tables = [
        "ab_tests",
        "sessions",
        "tenants",
        "notifications",
        "audit_logs",
        "knowledge_chunks"
    ]
    
    for table in tenanted_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON public.{table};")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")

    untenanted_tables = [
        "drug_interactions",
        "drug_affinities",
        "customer_cycles",
        "events",
        "pending_reminders",
        "ab_test_results"
    ]
    
    for table in untenanted_tables:
        op.execute(f"DROP POLICY IF EXISTS global_read_{table} ON public.{table};")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
