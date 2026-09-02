"""initial schema v4 — كل جداول AI-COS Pharmacy ERD (مع Tenant، وربط Supabase Auth)

Revision ID: 0001
Revises:
Create Date: 2026-08-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "tenants",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subdomain", sa.String(100), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "customers",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), primary_key=True),
        # يشاور على auth.users(id) بتاع Supabase — لا نخزن باسورد ولا google_id هنا
        sa.Column("auth_user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("age_group", sa.String(30), nullable=True),
        sa.Column("preferred_channel", sa.String(20), nullable=False, server_default="email"),
        sa.Column("preferred_language", sa.String(10), nullable=False, server_default="ar"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "drugs",
        sa.Column("drug_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, index=True),
        sa.Column("is_chronic", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("default_cycle_days", sa.Integer, nullable=False, server_default="30"),
    )

    op.create_table(
        "sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.customer_id"), nullable=True, index=True),
        sa.Column("device_info", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.session_id"), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "drug_interactions",
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("drug_id_a", postgresql.UUID(as_uuid=True), sa.ForeignKey("drugs.drug_id"), nullable=False),
        sa.Column("drug_id_b", postgresql.UUID(as_uuid=True), sa.ForeignKey("drugs.drug_id"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.CheckConstraint("drug_id_a < drug_id_b", name="ck_interaction_pair_order"),
        sa.UniqueConstraint("drug_id_a", "drug_id_b", name="uq_interaction_pair"),
    )

    op.create_table(
        "drug_affinities",
        sa.Column("affinity_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("drug_id_a", postgresql.UUID(as_uuid=True), sa.ForeignKey("drugs.drug_id"), nullable=False),
        sa.Column("drug_id_b", postgresql.UUID(as_uuid=True), sa.ForeignKey("drugs.drug_id"), nullable=False),
        sa.Column("affinity_type", sa.String(20), nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0"),
        sa.CheckConstraint("drug_id_a < drug_id_b", name="ck_affinity_pair_order"),
        sa.UniqueConstraint("drug_id_a", "drug_id_b", name="uq_affinity_pair"),
    )

    op.create_table(
        "orders",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.customer_id"), nullable=False, index=True),
        sa.Column("order_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("channel", sa.String(20), nullable=False, server_default="web"),
    )

    op.create_table(
        "order_items",
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.order_id"), nullable=False, index=True),
        sa.Column("drug_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drugs.drug_id"), nullable=False, index=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        "customer_cycles",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.customer_id"), primary_key=True),
        sa.Column("drug_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drugs.drug_id"), primary_key=True),
        sa.Column("avg_cycle_days", sa.Float, nullable=False),
        sa.Column("last_purchase_date", sa.Date, nullable=False),
        sa.Column("reminder_day", sa.Date, nullable=True),
    )

    op.create_table(
        "notifications",
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False, index=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.customer_id"), nullable=False, index=True),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("ab_variant", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("log_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.tenant_id"), nullable=False, index=True),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target_entity", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("customer_cycles")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("drug_affinities")
    op.drop_table("drug_interactions")
    op.drop_table("events")
    op.drop_table("sessions")
    op.drop_table("drugs")
    op.drop_table("customers")
    op.drop_table("tenants")
