"""
نموذج A/B Tests (FR-13) — جداول ab_tests + ab_test_results
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ABTest(Base):
    """تعريف تجربة A/B: اسمها، النوعان (discount | plain)، والمدة."""
    __tablename__ = "ab_tests"

    test_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    test_name:  Mapped[str]       = mapped_column(String(100), nullable=False)
    variant_a:  Mapped[str]       = mapped_column(String(50),  nullable=False)
    variant_b:  Mapped[str]       = mapped_column(String(50),  nullable=False)
    start_date: Mapped[date]      = mapped_column(Date(), nullable=False)
    end_date:   Mapped[date|None] = mapped_column(Date(), nullable=True)
    is_active:  Mapped[bool]      = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())


class ABTestResult(Base):
    """سجل لكل رسالة أُرسلت في إطار تجربة A/B مع حالة التحوّل (converted)."""
    __tablename__ = "ab_test_results"

    result_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ab_tests.test_id"), nullable=False, index=True)
    notification_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notifications.notification_id"), nullable=False)
    variant:         Mapped[str]       = mapped_column(String(50), nullable=False)
    converted:       Mapped[bool]      = mapped_column(Boolean(), nullable=False, default=False)
    created_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
