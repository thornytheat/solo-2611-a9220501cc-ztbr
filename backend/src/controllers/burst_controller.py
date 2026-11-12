"""爆发事件控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.middlewares.auth import brand_scope
from src.models.user import User
from src.schemas.burst import BurstDisposeRequest
from src.services import burst_service


def detect(db: Session, user: User, trace_id: str = "") -> dict:
    return burst_service.run_detection(db, user, brand_scope(user), trace_id)


def list_alerts(db: Session, user: User, level: str | None = None, status: str | None = None, limit: int = 40) -> dict:
    return burst_service.list_alerts(db, brand_scope(user), level, status, limit)


def dashboard(db: Session, user: User) -> dict:
    return burst_service.dashboard(db, brand_scope(user))


def detail(db: Session, alert_id: str, user: User) -> dict:
    return burst_service.detail(db, alert_id, brand_scope(user))


def claim(db: Session, alert_id: str, user: User, trace_id: str = "") -> dict:
    return burst_service.claim(db, alert_id, user, brand_scope(user), trace_id)


def dispose(db: Session, alert_id: str, payload: BurstDisposeRequest, user: User, trace_id: str = "") -> dict:
    return burst_service.dispose(db, alert_id, payload.status, payload.note, user, brand_scope(user), trace_id)
