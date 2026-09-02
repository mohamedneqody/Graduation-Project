"""Customer — بيانات العميل الإضافية فقط. المصادقة (باسورد/Google) يديرها Supabase Auth بالكامل
عبر جدول auth.users، وإحنا بس بنربط جدولنا بيه عن طريق auth_user_id."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # يشاور على auth.users(id) بتاع Supabase — لا نخزن باسورد ولا google_id هنا إطلاقًا
    auth_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )

    # email مُخزَّن هنا كنسخة للقراءة السريعة فقط (Source of Truth هو auth.users)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    age_group: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preferred_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="ar")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")
