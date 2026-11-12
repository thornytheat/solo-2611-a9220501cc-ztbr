"""导出控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.middlewares.auth import brand_scope
from src.models.user import User
from src.services import export_service


def preview(db: Session, user: User) -> dict:
    return export_service.build_daily_report(db, brand_scope(user))


def daily(db: Session, user: User, trace_id: str = "") -> dict:
    return export_service.export_daily(db, user, brand_scope(user), trace_id)
