"""采集控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import collect_service


def run(db: Session, user: User, trace_id: str = "") -> dict:
    return collect_service.run_collection(db, user, trace_id)


def runs(db: Session, limit: int = 8) -> dict:
    rows = collect_service.recent_runs(db, limit)
    return {"items": [{"id": row["id"], "created_at": row["created_at"], "actor_email": row["actor_email"], "detail": row["detail"]} for row in rows]}
