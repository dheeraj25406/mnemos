from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mnemos.db.base import Base, utc_now


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    memory_type: Mapped[str] = mapped_column(
        String(32), default="observation", index=True, nullable=False
    )
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(255), default="agent", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    access_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Bitemporal coordinates
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
    valid_to: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime(9999, 12, 31, tzinfo=None), index=True, nullable=False
    )
    recorded_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
    recorded_to: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime(9999, 12, 31, tzinfo=None), index=True, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("memories.id", ondelete="SET NULL"), nullable=True
    )
    consolidated_into_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("memory_consolidations.id", ondelete="SET NULL"), nullable=True
    )

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    embedding: Mapped["MemoryEmbedding"] = relationship(
        "MemoryEmbedding", back_populates="memory", uselist=False, cascade="all, delete-orphan"
    )
    facts: Mapped[list["Fact"]] = relationship(
        "Fact", back_populates="source_memory", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_memories_tenant_valid", "tenant_id", "valid_from", "valid_to"),
        Index("ix_memories_tenant_recorded", "tenant_id", "recorded_from", "recorded_to"),
        Index("ix_memories_tenant_content_hash", "tenant_id", "content_hash"),
    )
