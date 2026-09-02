"""p10_critical_fixes

Revision ID: p10critfixes
Revises: 5c8668fb5512
Create Date: 2026-08-13

P10 — Critical Bug Fixes (Forensic Audit P0 items)

Fixes three groups of critical bugs discovered by the forensic audit:

GROUP 1 — Missing orders columns (BUG-01)
  The orders table was created in 0001_initial_schema with only 6 columns.
  The ORM model (app/models/order.py) and OrderCreate schema define 4
  additional fields that were never added to the database:
    - shipping_name
    - shipping_phone
    - shipping_address
    - payment_method
  SQLAlchemy INSERT would crash with UndefinedColumn on every order creation.

GROUP 2 — Missing drugs clinical columns (BUG-02)
  The Drug ORM model defines 3 clinical data columns that were never added
  to the database via any migration:
    - active_ingredient
    - dosage
    - warnings
  These are referenced in DrugOut schema and MedicineDetailsModal frontend.

GROUP 3 — RLS deny-all on drug_interactions and drug_affinities (BUG-03)
  phase5_audit_hardening.py dropped the global_read_* policies on these
  tables and left the replacement commented out. PostgreSQL defaults to
  deny-all when RLS is enabled with no permissive policy. This silently
  breaks all drug interaction safety checks and cross-sell recommendations.
  This migration re-creates a global SELECT policy for the app role.

All changes are additive (nullable columns, new policies).
Safe to run on a live database. Idempotent via IF NOT EXISTS / IF EXISTS.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p10critfixes'
down_revision: Union[str, None] = '5c8668fb5512'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# GROUP 1 — Add missing orders columns (BUG-01)
# ---------------------------------------------------------------------------

def _add_orders_shipping_columns() -> None:
    """Add shipping and payment columns that are in the ORM but not in the DB."""
    # Use ADD COLUMN IF NOT EXISTS so re-running is safe
    op.execute("""
        ALTER TABLE public.orders
          ADD COLUMN IF NOT EXISTS shipping_name    VARCHAR(255),
          ADD COLUMN IF NOT EXISTS shipping_phone   VARCHAR(50),
          ADD COLUMN IF NOT EXISTS shipping_address VARCHAR(500),
          ADD COLUMN IF NOT EXISTS payment_method   VARCHAR(50) NOT NULL DEFAULT 'credit_card';
    """)


def _drop_orders_shipping_columns() -> None:
    """Reverse: remove the columns added above."""
    op.execute("""
        ALTER TABLE public.orders
          DROP COLUMN IF EXISTS shipping_name,
          DROP COLUMN IF EXISTS shipping_phone,
          DROP COLUMN IF EXISTS shipping_address,
          DROP COLUMN IF EXISTS payment_method;
    """)


# ---------------------------------------------------------------------------
# GROUP 2 — Add missing drugs clinical columns (BUG-02)
# ---------------------------------------------------------------------------

def _add_drugs_clinical_columns() -> None:
    """Add clinical data columns that are in the ORM but not in the DB."""
    op.execute("""
        ALTER TABLE public.drugs
          ADD COLUMN IF NOT EXISTS active_ingredient VARCHAR(255),
          ADD COLUMN IF NOT EXISTS dosage            VARCHAR(100),
          ADD COLUMN IF NOT EXISTS warnings          VARCHAR(1000);
    """)


def _drop_drugs_clinical_columns() -> None:
    """Reverse: remove the columns added above."""
    op.execute("""
        ALTER TABLE public.drugs
          DROP COLUMN IF EXISTS active_ingredient,
          DROP COLUMN IF EXISTS dosage,
          DROP COLUMN IF EXISTS warnings;
    """)


# ---------------------------------------------------------------------------
# GROUP 3 — Fix RLS deny-all on drug_interactions and drug_affinities (BUG-03)
# ---------------------------------------------------------------------------

def _restore_drug_table_rls_policies() -> None:
    """Re-create global SELECT policies for drug_interactions and drug_affinities.

    These tables store global (cross-tenant) drug data — there is no tenant_id
    column on them by design. The application role must be able to SELECT from
    them to perform drug interaction safety checks and cross-sell lookups.

    phase5_audit_hardening.py dropped global_read_drug_affinities and
    global_read_drug_interactions without replacing them, leaving both tables
    in a deny-all state for non-superuser roles.

    We restore a simple global SELECT policy (USING (true)) for both tables.
    INSERT / UPDATE / DELETE remain governed by the admin role grant, not RLS.
    """
    # drug_interactions
    op.execute(
        "DROP POLICY IF EXISTS global_read_drug_interactions ON public.drug_interactions;"
    )
    op.execute("""
        CREATE POLICY global_read_drug_interactions
          ON public.drug_interactions
          FOR SELECT
          USING (true);
    """)

    # drug_affinities
    op.execute(
        "DROP POLICY IF EXISTS global_read_drug_affinities ON public.drug_affinities;"
    )
    op.execute("""
        CREATE POLICY global_read_drug_affinities
          ON public.drug_affinities
          FOR SELECT
          USING (true);
    """)


def _drop_drug_table_rls_policies() -> None:
    """Reverse: remove the policies (returns to deny-all state)."""
    op.execute(
        "DROP POLICY IF EXISTS global_read_drug_interactions ON public.drug_interactions;"
    )
    op.execute(
        "DROP POLICY IF EXISTS global_read_drug_affinities ON public.drug_affinities;"
    )


# ---------------------------------------------------------------------------
# Alembic entry points
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ----------------------------------------------------------------
    # IMPORTANT: Supabase managed Postgres does not grant ALTER TABLE
    # to the application database role — only the Supabase superuser
    # (postgres) may modify table structure.
    #
    # The DDL for this migration has been extracted to:
    #   backend/p10_critical_fixes.sql
    #
    # To apply the fixes:
    #   1. Open Supabase Dashboard → SQL Editor
    #   2. Paste and run the contents of p10_critical_fixes.sql
    #   3. Then run:  alembic stamp p10_add_missing_columns_and_fix_rls
    #      to mark this revision as applied in the alembic_version table.
    #
    # What the SQL does:
    #   BUG-01: ALTER TABLE orders ADD COLUMN shipping_name / phone / address / payment_method
    #   BUG-02: ALTER TABLE drugs ADD COLUMN active_ingredient / dosage / warnings
    #   BUG-03: CREATE POLICY global_read on drug_interactions and drug_affinities
    # ----------------------------------------------------------------
    pass


def downgrade() -> None:
    # To reverse: run the SQL manually in Supabase SQL Editor:
    #   ALTER TABLE orders DROP COLUMN IF EXISTS shipping_name, shipping_phone, shipping_address, payment_method;
    #   ALTER TABLE drugs  DROP COLUMN IF EXISTS active_ingredient, dosage, warnings;
    #   DROP POLICY IF EXISTS global_read_drug_interactions ON drug_interactions;
    #   DROP POLICY IF EXISTS global_read_drug_affinities   ON drug_affinities;
    pass

