"""add image_url to drugs

Revision ID: 0fd4baccac30
Revises: 0001
Create Date: 2026-08-03 22:10:56.926549
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0fd4baccac30'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('drugs', sa.Column('image_url', sa.String(length=500), nullable=True))

def downgrade() -> None:
    op.drop_column('drugs', 'image_url')
