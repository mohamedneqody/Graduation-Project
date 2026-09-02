import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Float, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PrescriptionAnalysis(Base):
    __tablename__ = "prescription_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prescription_analyses.id"), nullable=False, index=True)
    raw_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_illegible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    match_status: Mapped[str] = mapped_column(String(50), nullable=False)
    matched_drug_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidates: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    pharmacist_decision: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    pharmacist_selected_drug_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.drug_id"), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
