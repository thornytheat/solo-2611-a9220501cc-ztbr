from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import mention_controller
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.mention import MentionReviewRequest

router = APIRouter(tags=["mention"])


@router.get("/mentions/review-queue")
def review_queue(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("mentions:review")),
) -> dict:
    return mention_controller.review_queue(db, user, limit)


@router.get("/mentions")
def list_mentions(
    group_code: str | None = None,
    source_code: str | None = None,
    label: str | None = None,
    review_status: str | None = None,
    q: str | None = None,
    days: int | None = Query(default=None, ge=1, le=30),
    sort: str = Query(default="published_desc"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("mentions:read")),
) -> dict:
    return mention_controller.list_mentions(
        db,
        user,
        group_code=group_code,
        source_code=source_code,
        label=label,
        review_status=review_status,
        q=q,
        days=days,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/mentions/{mention_id}")
def detail(
    mention_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("mentions:read")),
) -> dict:
    return mention_controller.detail(db, mention_id, user)


@router.post("/mentions/{mention_id}/review")
def review(
    mention_id: str,
    payload: MentionReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("mentions:review")),
) -> dict:
    return mention_controller.review(db, mention_id, payload, user, getattr(request.state, "trace_id", ""))
