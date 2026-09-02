"""add_roles_and_rls

Revision ID: 6da1c746fdff
Revises: a165179f481d
Create Date: 2026-08-10 05:10:42.441701
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6da1c746fdff'
down_revision: Union[str, None] = 'a165179f481d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column
    op.add_column('customers', sa.Column('role', sa.String(50), server_default='customer', nullable=False))
    
    # RLS Function
    op.execute("""
        CREATE OR REPLACE FUNCTION current_user_tenant_id()
        RETURNS uuid
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT tenant_id FROM customers WHERE auth_user_id = auth.uid() LIMIT 1;
        $$;
    """)

    # Customers
    op.execute("ALTER TABLE customers ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_customers ON customers;")
    op.execute("""
        CREATE POLICY tenant_isolation_customers ON customers
          FOR SELECT USING (tenant_id = current_user_tenant_id());
    """)

    # Drugs
    op.execute("ALTER TABLE drugs ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS global_read_drugs ON drugs;")
    op.execute("""
        CREATE POLICY global_read_drugs ON drugs
          FOR SELECT USING (auth.role() = 'authenticated');
    """)

    # Orders
    op.execute("ALTER TABLE orders ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_orders ON orders;")
    op.execute("""
        CREATE POLICY tenant_isolation_orders ON orders
          FOR ALL USING (tenant_id = current_user_tenant_id());
    """)

    # Order Items
    op.execute("ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_order_items ON order_items;")
    op.execute("""
        CREATE POLICY tenant_isolation_order_items ON order_items
          FOR ALL
          USING (EXISTS (
            SELECT 1 FROM orders o
            WHERE o.order_id = order_items.order_id
            AND o.tenant_id = current_user_tenant_id()
          ))
          WITH CHECK (EXISTS (
            SELECT 1 FROM orders o
            WHERE o.order_id = order_items.order_id
            AND o.tenant_id = current_user_tenant_id()
          ));
    """)

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_order_items ON order_items;")
    op.execute("ALTER TABLE order_items DISABLE ROW LEVEL SECURITY;")
    
    op.execute("DROP POLICY IF EXISTS tenant_isolation_orders ON orders;")
    op.execute("ALTER TABLE orders DISABLE ROW LEVEL SECURITY;")
    
    op.execute("DROP POLICY IF EXISTS global_read_drugs ON drugs;")
    op.execute("ALTER TABLE drugs DISABLE ROW LEVEL SECURITY;")
    
    op.execute("DROP POLICY IF EXISTS tenant_isolation_customers ON customers;")
    op.execute("ALTER TABLE customers DISABLE ROW LEVEL SECURITY;")
    
    op.execute("DROP FUNCTION IF EXISTS current_user_tenant_id();")
    op.drop_column('customers', 'role')
