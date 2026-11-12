"""KeywordGroup：关键词组 + 同义词 + 排除词（实体 1/4）。

自然键 = code；一个品牌下多个主题组（如 coffee-foreign「咖啡-异物」）。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, new_uuid, utcnow


class KeywordGroup(Base):
    __tablename__ = "keyword_groups"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    keywords: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    synonyms: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    excludes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    z_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    min_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    owner_note: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
