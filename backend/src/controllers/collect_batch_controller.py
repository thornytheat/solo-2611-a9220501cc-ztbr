"""补采批次控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.middlewares.auth import brand_scope
from src.models.user import User
from src.schemas.collect_batch import CollectBatchCreateRequest
from src.services import collect_batch_service
from src.utils.errors import AppError


def create(db: Session, user: User, payload: CollectBatchCreateRequest, trace_id: str) -> dict:
    return collect_batch_service.create_batch(
        db,
        user,
        brand_key=payload.brand_key,
        source_codes=tuple(payload.source_codes),
        window_start=payload.window_start,
        window_end=payload.window_end,
        trace_id=trace_id,
    )


def run(db: Session, user: User, batch_id: str, trace_id: str) -> dict:
    _ensure_access(db, user, batch_id)
    return collect_batch_service.run_batch(db, user, batch_id, trace_id)


def list_batches(db: Session, user: User, limit: int, offset: int) -> dict:
    return collect_batch_service.list_batches(db, brand_scope(user), limit, offset)


def detail(db: Session, user: User, batch_id: str) -> dict:
    _ensure_access(db, user, batch_id)
    return collect_batch_service.detail(db, batch_id, user)


def items(db: Session, user: User, batch_id: str, source_code: str | None, status: str | None,
          limit: int, offset: int) -> dict:
    _ensure_access(db, user, batch_id)
    return collect_batch_service.items(
        db, batch_id, source_code=source_code, status=status, limit=limit, offset=offset
    )


def reconciliation(db: Session, user: User, batch_id: str) -> dict:
    _ensure_access(db, user, batch_id)
    return collect_batch_service.reconciliation(db, batch_id)


def source_health(db: Session, user: User) -> dict:
    from src.services.analysis.source_gateway import gateway

    return {"items": gateway.health()}


def set_outage(db: Session, user: User, source_code: str, online: bool, reason: str) -> dict:
    from src.constants.sources import SOURCE_CODES
    from src.services.analysis.source_gateway import gateway

    if source_code not in SOURCE_CODES:
        raise AppError(codes.VALIDATION_ERROR, "来源不合法", f"source={source_code}")
    if online:
        gateway.clear_outage(source_code)
    else:
        gateway.set_outage(source_code, reason or "simulated outage")
    return {"items": gateway.health()}


def _ensure_access(db: Session, user: User, batch_id: str) -> None:
    """品牌方账号只能访问自己品牌的批次（接口权限本身已拦截 client 写操作）。"""
    scope = brand_scope(user)
    if not scope:
        return
    batch = collect_batch_service.detail(db, batch_id)
    if batch["brand_key"] != scope:
        raise AppError(codes.BRAND_SCOPE_DENIED, "该批次不属于你负责的品牌", "brand mismatch")
