from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mnemos.db.base import Base, utc_now


class MemoryConsolidation(Base):
    __tablename__ = "memory_consolidations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    consolidation_type: Mapped[str] = mapped_column(
        String(64), default="temporal_summary", index=True, nullable=False
    )  # duplicate_merge, temporal_summary, entity_summary, compression
    summary_content: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="SET NULL"), index=True, nullable=True
    )
    original_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    original_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compressed_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compression_ratio: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    members: Mapped[list["ConsolidationMember"]] = relationship(
        "ConsolidationMember", back_populates="consolidation", cascade="all, delete-orphan"
    )


class ConsolidationMember(Base):
    __tablename__ = "consolidation_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consolidation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("memory_consolidations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    memory_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("memories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    contribution_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    consolidation: Mapped[MemoryConsolidation] = relationship(
        "MemoryConsolidation", back_populates="members"
    )

    __table_args__ = (
        Index("ix_consolidation_members_pair", "consolidation_id", "memory_id"),
    )
