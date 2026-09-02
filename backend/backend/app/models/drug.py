"""Drug + DrugInteraction (تعارض) + DrugAffinity (توافق/بيع مرتبط).

ملاحظة تصميمية: في DrugInteraction وDrugAffinity، نفرض قيد CheckConstraint
يضمن drug_id_a < drug_id_b دائمًا (بترتيب النص) لمنع تسجيل نفس الزوج مرتين
بترتيب معكوس (A,B) و(B,A) كسجلين منفصلين بالخطأ، مع UniqueConstraint على الزوج.
"""
import uuid
from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, Float, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Drug(Base):
    __tablename__ = "drugs"

    drug_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # مثال: "مزمن - ضغط"
    is_chronic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    default_cycle_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)  # Fallback لعميل جديد
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class DrugInteraction(Base):
    """جدول تعارض الأدوية — يُفحَص قبل إتمام أي طلب متعدد الأدوية."""
    __tablename__ = "drug_interactions"
    __table_args__ = (
        CheckConstraint("drug_id_a < drug_id_b", name="ck_interaction_pair_order"),
        UniqueConstraint("drug_id_a", "drug_id_b", name="uq_interaction_pair"),
    )

    interaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id_a: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=False)
    drug_id_b: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low | medium | high
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class DrugAffinity(Base):
    """جدول التوافق/البيع المرتبط (Cross-sell)."""
    __tablename__ = "drug_affinities"
    __table_args__ = (
        CheckConstraint("drug_id_a < drug_id_b", name="ck_affinity_pair_order"),
        UniqueConstraint("drug_id_a", "drug_id_b", name="uq_affinity_pair"),
    )

    affinity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id_a: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=False)
    drug_id_b: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=False)
    affinity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # complementary | market_basket
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
