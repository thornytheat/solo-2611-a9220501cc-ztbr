"""SentimentScore：情感分 + 命中证据 + 人工复核态（实体 3/4）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid


class SentimentScore(Base, TimestampMixin):
    __tablename__ = "sentiment_scores"
    __table_args__ = (
        UniqueConstraint("mention_id", name="uq_sentiment_mention"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.mentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    label: Mapped[str] = mapped_column(String(12), nullable=False, default="neu", index=True)
    final_label: Mapped[str] = mapped_column(String(12), nullable=False, default="neu", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hits: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    degree_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rhetoric_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exclaim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False, default="sent-1.0.0")
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="auto", index=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewer_email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    review_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mention = relationship("Mention", back_populates="sentiment")
