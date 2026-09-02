import uuid
from sqlalchemy import Column, Integer, Numeric, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    inventory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    drug_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=False, index=True
    )
    stock_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    tenant_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)  # Null means use global base_price
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

