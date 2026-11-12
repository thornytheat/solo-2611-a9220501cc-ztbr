"""BurstAlert：关键词组×小时桶的爆发事件（实体 4/4）。

自然键 = (group_id, window_start)，重复检测只更新指标不新建。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class BurstAlert(Base, TimestampMixin):
    __tablename__ = "burst_alerts"
    __table_args__ = (
        UniqueConstraint("group_id", "window_start", name="uq_burst_group_window"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.keyword_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    baseline_mean: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    baseline_std: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    z_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    level: Mapped[str] = mapped_column(String(12), nullable=False, default="watch", index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)
    merged_windows: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    baseline_series: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sample_titles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    claimed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    claimed_by_email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposition_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detection_version: Mapped[str] = mapped_column(String(20), nullable=False, default="burst-1.0.0")

    group = relationship("KeywordGroup", lazy="joined")
