"""Mention：一条采集到的提及（实体 2/4）。

自然键 = external_id（来源内原生 id），同时用 content_hash 做二次去重。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class Mention(Base, TimestampMixin):
    __tablename__ = "mentions"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_mention_external"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    external_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.keyword_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_code: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    author_followers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    url: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    engagement: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)

    group = relationship("KeywordGroup", lazy="joined")
    sentiment = relationship(
        "SentimentScore",
        back_populates="mention",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )
