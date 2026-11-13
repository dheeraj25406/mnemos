from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mnemos.db.base import Base, utc_now


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    memory_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("memories.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    embedding = mapped_column(Vector(384), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=384, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), default="BAAI/bge-small-en-v1.5", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    memory: Mapped["Memory"] = relationship("Memory", back_populates="embedding")

    __table_args__ = (
        Index("ix_memory_embeddings_tenant", "tenant_id"),
    )
