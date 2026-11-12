"""补采批次路由：批次的创建、续跑、回看、台账明细与对账。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import collect_batch_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.collect_batch import CollectBatchCreateRequest

router = APIRouter(tags=["collect-batch"])


@router.post("/collect/batches")
def create_batch(
    payload: CollectBatchCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
    _: None = rate_limit("collect"),
) -> dict:
    return collect_batch_controller.create(
        db, user, payload, getattr(request.state, "trace_id", "")
    )


@router.post("/collect/batches/{batch_id}/run")
def run_batch(
    batch_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
    _: None = rate_limit("collect"),
) -> dict:
    return collect_batch_controller.run(
        db, user, batch_id, getattr(request.state, "trace_id", "")
    )


@router.get("/collect/batches")
def list_batches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
) -> dict:
    return collect_batch_controller.list_batches(db, user, limit, offset)


@router.get("/collect/batches/{batch_id}")
def batch_detail(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
) -> dict:
    return collect_batch_controller.detail(db, user, batch_id)


@router.get("/collect/batches/{batch_id}/items")
def batch_items(
    batch_id: str,
    source_code: str | None = None,
    status: str | None = Query(default=None, pattern="^(pending|inserted|duplicate|failed|skipped)$"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
) -> dict:
    return collect_batch_controller.items(db, user, batch_id, source_code, status, limit, offset)


@router.get("/collect/batches/{batch_id}/reconciliation")
def batch_reconciliation(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
) -> dict:
    return collect_batch_controller.reconciliation(db, user, batch_id)


@router.get("/collect/source-health")
def source_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
) -> dict:
    return collect_batch_controller.source_health(db, user)


@router.post("/collect/source-health/{source_code}")
def set_source_health(
    source_code: str,
    online: bool = Query(..., description="true 恢复；false 注入中断"),
    reason: str = Query(default="", max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("collect:run")),
    _: None = rate_limit("collect"),
) -> dict:
    return collect_batch_controller.set_outage(
        db, user, source_code, online, reason
    )
