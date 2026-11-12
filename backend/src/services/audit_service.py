"""审计日志写入（横切关注点：审计）。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog
from src.models.user import User


def record(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    entity_type: str = "",
    entity_id: object = "",
    detail: dict[str, Any] | None = None,
    trace_id: str = "",
) -> AuditLog:
    entry = AuditLog(
        action=action,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "",
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else "",
        detail=detail or {},
        trace_id=trace_id,
    )
    db.add(entry)
    db.flush()
    return entry


def serialize(entry: AuditLog) -> dict:
    return {
        "id": str(entry.id),
        "action": entry.action,
        "actor_email": entry.actor_email,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "detail": entry.detail,
        "trace_id": entry.trace_id,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def recent(db: Session, limit: int = 60, action: str | None = None) -> list[dict]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = db.execute(stmt).scalars().all()
    return [serialize(row) for row in rows]


def for_entity(db: Session, entity_type: str, entity_id: str, limit: int = 10) -> list[dict]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return [serialize(row) for row in db.execute(stmt).scalars().all()]
