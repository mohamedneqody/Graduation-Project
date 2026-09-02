"""supabase_reads_and_rpc

Revision ID: 0c97e08a5308
Revises: 8bde7c490701
Create Date: 2026-08-10 14:12:24.450455
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0c97e08a5308'
down_revision: Union[str, None] = '8bde7c490701'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Allow public (anon and authenticated) reads for drugs table
    op.execute("DROP POLICY IF EXISTS global_read_drugs ON public.drugs;")
    op.execute("""
        CREATE POLICY global_read_drugs ON public.drugs
        FOR SELECT
        USING (true);
    """)

    # Create get_drug_categories RPC for Supabase to use
    op.execute("""
        CREATE OR REPLACE FUNCTION get_drug_categories()
        RETURNS TABLE (name VARCHAR, count BIGINT)
        SECURITY DEFINER
        AS $$
        BEGIN
            RETURN QUERY
            SELECT category AS name, COUNT(drug_id) AS count
            FROM public.drugs
            GROUP BY category
            ORDER BY count DESC;
        END;
        $$ LANGUAGE plpgsql;
    """)

def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_drug_categories();")
    
    # Revert to authenticated only
    op.execute("DROP POLICY IF EXISTS global_read_drugs ON public.drugs;")
    op.execute("""
        CREATE POLICY global_read_drugs ON public.drugs
        FOR SELECT
        USING (auth.role() = 'authenticated'::text);
    """)
