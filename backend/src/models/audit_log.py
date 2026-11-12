"""AuditLog：横切审计日志（登录、采集、复核、认领、处置、导出）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, new_uuid, utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
