from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mnemos.db.base import Base, utc_now


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_entity_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("entities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    fact_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("facts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_memory_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("memories.id", ondelete="SET NULL"), index=True, nullable=True
    )

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
    properties: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    source_entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[source_entity_id])
    target_entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[target_entity_id])

    __table_args__ = (
        Index("ix_relationships_traversal", "tenant_id", "source_entity_id", "relation_type"),
        Index("ix_relationships_reverse_traversal", "tenant_id", "target_entity_id", "relation_type"),
        Index("ix_relationships_bitemporal", "tenant_id", "valid_from", "valid_to", "recorded_from", "recorded_to"),
    )
