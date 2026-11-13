from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mnemos.db.base import Base, utc_now


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_memory_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("memories.id", ondelete="SET NULL"), index=True, nullable=True
    )
    subject_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    predicate: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    object_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="SET NULL"), index=True, nullable=True
    )
    object_literal: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    is_retracted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("facts.id", ondelete="SET NULL"), nullable=True
    )

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # ORM relationships
    source_memory: Mapped["Memory"] = relationship("Memory", back_populates="facts")
    subject: Mapped["Entity"] = relationship("Entity", foreign_keys=[subject_id])
    object_entity: Mapped["Entity | None"] = relationship("Entity", foreign_keys=[object_id])

    __table_args__ = (
        Index("ix_facts_bitemporal_lookup", "tenant_id", "subject_id", "predicate", "valid_from", "valid_to"),
        Index("ix_facts_recorded_lookup", "tenant_id", "recorded_from", "recorded_to"),
    )
