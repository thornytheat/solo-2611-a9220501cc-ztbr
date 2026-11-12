from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import burst_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.burst import BurstDisposeRequest

router = APIRouter(tags=["burst"])


@router.get("/bursts/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("bursts:read")),
) -> dict:
    return burst_controller.dashboard(db, user)


@router.post("/bursts/detect")
def detect(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("bursts:detect")),
    _: None = rate_limit("detect"),
) -> dict:
    return burst_controller.detect(db, user, getattr(request.state, "trace_id", ""))


@router.get("/bursts")
def list_alerts(
    level: str | None = None,
    status: str | None = None,
    limit: int = Query(default=40, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("bursts:read")),
) -> dict:
    return burst_controller.list_alerts(db, user, level, status, limit)


@router.get("/bursts/{alert_id}")
def detail(
    alert_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("bursts:read")),
) -> dict:
    return burst_controller.detail(db, alert_id, user)


@router.post("/bursts/{alert_id}/claim")
def claim(
    alert_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("bursts:claim")),
) -> dict:
    return burst_controller.claim(db, alert_id, user, getattr(request.state, "trace_id", ""))


@router.post("/bursts/{alert_id}/dispose")
def dispose(
    alert_id: str,
    payload: BurstDisposeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("bursts:dispose")),
) -> dict:
    return burst_controller.dispose(db, alert_id, payload, user, getattr(request.state, "trace_id", ""))
