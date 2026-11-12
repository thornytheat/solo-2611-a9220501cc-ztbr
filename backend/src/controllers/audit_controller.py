"""审计控制器（仅 admin）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import audit_service


def recent(db: Session, limit: int = 60, action: str | None = None) -> dict:
    return {"items": audit_service.recent(db, limit=limit, action=action)}
