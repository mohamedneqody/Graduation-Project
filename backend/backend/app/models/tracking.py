"""CustomerCycle (مُشتق) + Notification + AuditLog."""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CustomerCycle(Base):
    """جدول مُشتق (Derived) — يُعاد حسابه يوميًا من Orders، وليس مصدر حقيقة أساسي.
    المفتاح الأساسي مُركَّب (Composite PK) من customer_id + drug_id معًا."""
    __tablename__ = "customer_cycles"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.customer_id"), primary_key=True
    )
    drug_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drugs.drug_id"), primary_key=True
    )
    avg_cycle_days: Mapped[float] = mapped_column(Float, nullable=False)
    last_purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    reminder_day: Mapped[date | None] = mapped_column(Date, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    notification_type: Mapped[str] = mapped_column(String(30), nullable=False)  # reminder | cross_sell
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # whatsapp | email
    ab_variant: Mapped[str | None] = mapped_column(String(20), nullable=True)  # discount | plain
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending|sent|failed|opened
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)  # customer_id أو اسم النظام الآلي
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PendingReminder(Base):
    """
    قائمة انتظار التذكيرات — النمط (أ) المعتمَد:
    FastAPI يُسجِّل القرار هنا، و n8n يـ poll هذا الجدول كل صباح
    ثم يُرسِل ويُحدِّث الحالة إلى 'sent' أو 'failed'.

    قرار معماري موثَّق في SAD §6.4:
      n8n = المُحرِّك | FastAPI = المصدر
    """
    __tablename__ = "pending_reminders"

    reminder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    drug_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")  # email | whatsapp
    decision: Mapped[str] = mapped_column(String(20), nullable=False)      # auto_send | human_review
    cycle_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    churn_probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_days: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending | sent | failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
