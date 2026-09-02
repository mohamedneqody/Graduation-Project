"""phase9_fix_rls

Revision ID: 5c8668fb5512
Revises: phase8_chain_per_session_fix
Create Date: 2026-08-11 16:28:31.953013
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5c8668fb5512'
down_revision: Union[str, None] = 'phase8_chain_per_session_fix'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Originally attempted to ALTER events.event_seq NOT NULL and fix RLS policies.
    # The ALTER TABLE events ... fails on Supabase managed Postgres with
    # InsufficientPrivilegeError (must be owner of table events).
    # The RLS policy changes for customers/drugs were also incorrect (drugs has no tenant_id).
    # All valid fixes have been moved to p10_add_missing_columns_and_fix_rls.
    # This migration is intentionally a no-op to preserve chain integrity.
    pass


def downgrade() -> None:
    pass

