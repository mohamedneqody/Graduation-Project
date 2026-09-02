"""KnowledgeChunk — قاعدة المعرفة الخاصة بالبوت (RAG) عبر pgvector."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database.session import Base

# 384 = بُعد الـ Embeddings الافتراضي لنموذج all-MiniLM-L6-v2 (أو المتعدد اللغات المكافئ)
EMBEDDING_DIM = 384


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # drug_info | policy | faq
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
