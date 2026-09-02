"""add ab_tests table (FR-13)

Revision ID: 0003_ab_tests
Revises: 0fd4baccac30
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_ab_tests"
down_revision = "0fd4baccac30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ab_tests",
        sa.Column("test_id",     postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False, index=True),
        sa.Column("test_name",   sa.String(100), nullable=False),            # e.g. "reminder_discount_vs_plain"
        sa.Column("variant_a",   sa.String(50),  nullable=False),            # e.g. "discount"
        sa.Column("variant_b",   sa.String(50),  nullable=False),            # e.g. "plain"
        sa.Column("start_date",  sa.Date(),       nullable=False),
        sa.Column("end_date",    sa.Date(),       nullable=True),
        sa.Column("is_active",   sa.Boolean(),   nullable=False, server_default=sa.true()),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # جدول النتائج — سجل لكل notification أُرسلت بأي variant
    op.create_table(
        "ab_test_results",
        sa.Column("result_id",       postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("test_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("ab_tests.test_id"), nullable=False, index=True),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notifications.notification_id"), nullable=False),
        sa.Column("variant",         sa.String(50), nullable=False),          # discount | plain
        sa.Column("converted",       sa.Boolean(), nullable=False, server_default=sa.false()),  # هل اشترى بعدها؟
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ab_test_results")
    op.drop_table("ab_tests")
