from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import group_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.group import GroupCreateRequest, GroupTrialRequest, GroupUpdateRequest

router = APIRouter(tags=["group"])


@router.get("/groups")
def list_groups(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("groups:read")),
) -> dict:
    return group_controller.list_groups(db, user)


@router.post("/groups")
def create_group(
    payload: GroupCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("groups:write")),
) -> dict:
    return group_controller.create(db, payload, user, getattr(request.state, "trace_id", ""))


@router.patch("/groups/{group_id}")
def update_group(
    group_id: str,
    payload: GroupUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("groups:write")),
) -> dict:
    return group_controller.update(db, group_id, payload, user, getattr(request.state, "trace_id", ""))


@router.post("/groups/trial")
def trial(
    payload: GroupTrialRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("groups:trial")),
    _: None = rate_limit("default"),
) -> dict:
    return group_controller.trial(db, payload, user, getattr(request.state, "trace_id", ""))
