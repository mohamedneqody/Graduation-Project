"""add_tenant_id_to_prescriptions

Revision ID: 41e5683a3f96
Revises: 739be44c2f1a
Create Date: 2026-08-23 05:11:35.245745
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '41e5683a3f96'
down_revision: Union[str, None] = '79b5a57ca6d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prescriptions', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    
def downgrade() -> None:
    op.drop_column('prescriptions', 'tenant_id')
